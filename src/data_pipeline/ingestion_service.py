"""Repository-backed ingestion orchestration for provider results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.database.repository import IngestionBatchRepository, JobPostingRepository
from src.observability.logging import event_logger

from .models import JobPosting
from .providers import JobPostingProvider, JobSearchRequest
from .source_policy import SourcePolicyDecision, evaluate_source
from .validation import validate_job_postings


class IngestionPolicyError(ValueError):
    """Raised when a requested provider does not pass source governance."""

    def __init__(self, blocked_sources: list[SourcePolicyDecision]):
        self.blocked_sources = blocked_sources
        details = "; ".join(
            f"{decision.source}: {decision.reason}" for decision in blocked_sources
        )
        super().__init__(f"Blocked ingestion sources: {details}")


@dataclass(frozen=True)
class ProviderIngestionSummary:
    """Summary for one provider during an ingestion batch."""

    source: str
    legal_basis: str | None
    allowed: bool
    fetched_count: int
    saved_count: int
    reason: str


@dataclass(frozen=True)
class IngestionBatchSummary:
    """Stable summary returned after repository-backed ingestion."""

    status: str
    ingestion_batch_id: str
    sources: list[str]
    keywords: list[str]
    limit_per_source: int
    fetched_count: int
    saved_count: int
    expired_count: int
    active_jobs_after: int
    provider_results: list[ProviderIngestionSummary]
    started_at: datetime
    finished_at: datetime
    duration_seconds: float

    def to_dict(self) -> dict:
        """Return JSON-serializable response data."""
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["finished_at"] = self.finished_at.isoformat()
        return payload


class IngestionService:
    """Fetch approved provider data, validate it, and persist it to the repository."""

    def __init__(
        self,
        providers: dict[str, JobPostingProvider],
        repository: JobPostingRepository,
        batch_repository: IngestionBatchRepository | None = None,
    ):
        self.providers = providers
        self.repository = repository
        self.batch_repository = batch_repository or IngestionBatchRepository(repository.session)

    @staticmethod
    def _provider_key(source: str) -> str:
        return source.strip().lower()

    def _get_provider(self, source: str) -> JobPostingProvider:
        source_key = self._provider_key(source)
        provider = self.providers.get(source_key)
        if provider is None:
            raise ValueError(f"No provider registered for source '{source}'.")
        return provider

    def _evaluate_sources(self, sources: list[str]) -> list[SourcePolicyDecision]:
        decisions: list[SourcePolicyDecision] = []
        for source in sources:
            provider = self._get_provider(source)
            decisions.append(evaluate_source(provider.source_id, getattr(provider, "legal_basis", None)))
        return decisions

    @staticmethod
    def _attach_batch_id(jobs: list[JobPosting], batch_id: str) -> list[JobPosting]:
        stamped_jobs = []
        for job in jobs:
            update = {
                "ingestion_batch_id": batch_id,
                "last_seen_at": job.last_seen_at or datetime.now(UTC),
                "is_expired": False,
            }
            if hasattr(job, "model_copy"):
                stamped_jobs.append(job.model_copy(update=update))
            else:  # pragma: no cover - Pydantic v1 compatibility.
                stamped_jobs.append(job.copy(update=update))
        return stamped_jobs

    def ingest(
        self,
        sources: list[str],
        keywords: list[str],
        limit_per_source: int = 100,
        mark_expired: bool = True,
        dry_run: bool = False,
    ) -> IngestionBatchSummary:
        """Run one provider ingestion batch and persist normalized jobs."""
        if not sources:
            raise ValueError("At least one source is required for ingestion.")

        started_at = datetime.now(UTC)
        batch_id = f"ing_{started_at.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        batch_log = event_logger(
            "ingestion_batch",
            ingestion_batch_id=batch_id,
            sources=sources,
            keywords=keywords,
            limit_per_source=limit_per_source,
            dry_run=dry_run,
            mark_expired=mark_expired,
        )
        batch_log.info("Ingestion batch started.")
        if not dry_run:
            self.batch_repository.start_batch(
                batch_id=batch_id,
                source=[self._provider_key(source) for source in sources],
                started_at=started_at,
            )
        decisions = self._evaluate_sources(sources)
        blocked = [decision for decision in decisions if not decision.allowed]
        if blocked:
            event_logger(
                "ingestion_blocked",
                ingestion_batch_id=batch_id,
                blocked_sources=[decision.source for decision in blocked],
            ).warning("Ingestion blocked by source governance.")
            if not dry_run:
                self.batch_repository.fail_batch(
                    batch_id=batch_id,
                    error_message=str(IngestionPolicyError(blocked)),
                )
            raise IngestionPolicyError(blocked)

        request = JobSearchRequest(keywords=keywords, limit=limit_per_source)
        provider_results: list[ProviderIngestionSummary] = []
        fetched_jobs: list[JobPosting] = []

        try:
            for source in sources:
                provider = self._get_provider(source)
                source_key = self._provider_key(provider.source_id)
                event_logger(
                    "ingestion_provider_fetch",
                    ingestion_batch_id=batch_id,
                    source=source_key,
                    legal_basis=getattr(provider, "legal_basis", None),
                ).info("Provider fetch started.")
                jobs = provider.fetch(request)
                stamped_jobs = self._attach_batch_id(jobs, batch_id)
                validate_job_postings(stamped_jobs)
                saved_jobs = [] if dry_run else self.repository.save_jobs(stamped_jobs)
                fetched_jobs.extend(stamped_jobs)
                provider_results.append(
                    ProviderIngestionSummary(
                        source=source_key,
                        legal_basis=getattr(provider, "legal_basis", None),
                        allowed=True,
                        fetched_count=len(stamped_jobs),
                        saved_count=len(saved_jobs),
                        reason=(
                            "Source passed governance and validation; repository write skipped for dry run."
                            if dry_run
                            else "Source passed governance, validation, and repository persistence."
                        ),
                    ),
                )
                event_logger(
                    "ingestion_provider_result",
                    ingestion_batch_id=batch_id,
                    source=source_key,
                    fetched_count=len(stamped_jobs),
                    saved_count=len(saved_jobs),
                    dry_run=dry_run,
                ).info("Provider ingestion result recorded.")

            expired_count = self.repository.mark_expired() if mark_expired and not dry_run else 0
            finished_at = datetime.now(UTC)
            active_jobs_after = len(self.repository.list_job_dicts())

            summary = IngestionBatchSummary(
                status="dry_run" if dry_run else "completed",
                ingestion_batch_id=batch_id,
                sources=[self._provider_key(source) for source in sources],
                keywords=keywords,
                limit_per_source=limit_per_source,
                fetched_count=len(fetched_jobs),
                saved_count=sum(result.saved_count for result in provider_results),
                expired_count=expired_count,
                active_jobs_after=active_jobs_after,
                provider_results=provider_results,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=round((finished_at - started_at).total_seconds(), 3),
            )
        except Exception as exc:
            if not dry_run:
                self.batch_repository.fail_batch(
                    batch_id=batch_id,
                    error_message=str(exc),
                )
            raise

        if not dry_run:
            self.batch_repository.complete_batch(
                batch_id=batch_id,
                status=summary.status,
                fetched_count=summary.fetched_count,
                saved_count=summary.saved_count,
                expired_count=summary.expired_count,
                finished_at=summary.finished_at,
            )
        event_logger(
            "ingestion_batch_completed",
            ingestion_batch_id=batch_id,
            status=summary.status,
            fetched_count=summary.fetched_count,
            saved_count=summary.saved_count,
            expired_count=summary.expired_count,
            active_jobs_after=summary.active_jobs_after,
            duration_seconds=summary.duration_seconds,
        ).info("Ingestion batch completed.")
        return summary
