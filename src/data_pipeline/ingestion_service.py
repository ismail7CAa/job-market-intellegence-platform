"""Repository-backed ingestion orchestration for provider results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from loguru import logger

from src.database.repository import JobPostingRepository

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
    ):
        self.providers = providers
        self.repository = repository

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
    ) -> IngestionBatchSummary:
        """Run one provider ingestion batch and persist normalized jobs."""
        if not sources:
            raise ValueError("At least one source is required for ingestion.")

        started_at = datetime.now(UTC)
        batch_id = f"ing_{started_at.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        decisions = self._evaluate_sources(sources)
        blocked = [decision for decision in decisions if not decision.allowed]
        if blocked:
            raise IngestionPolicyError(blocked)

        request = JobSearchRequest(keywords=keywords, limit=limit_per_source)
        provider_results: list[ProviderIngestionSummary] = []
        fetched_jobs: list[JobPosting] = []

        for source in sources:
            provider = self._get_provider(source)
            source_key = self._provider_key(provider.source_id)
            logger.info("ingestion_fetch source={} batch_id={}", source_key, batch_id)
            jobs = provider.fetch(request)
            stamped_jobs = self._attach_batch_id(jobs, batch_id)
            validate_job_postings(stamped_jobs)
            saved_jobs = self.repository.save_jobs(stamped_jobs)
            fetched_jobs.extend(stamped_jobs)
            provider_results.append(
                ProviderIngestionSummary(
                    source=source_key,
                    legal_basis=getattr(provider, "legal_basis", None),
                    allowed=True,
                    fetched_count=len(stamped_jobs),
                    saved_count=len(saved_jobs),
                    reason="Source passed governance, validation, and repository persistence.",
                )
            )
            logger.info(
                "ingestion_saved source={} batch_id={} fetched={} saved={}",
                source_key,
                batch_id,
                len(stamped_jobs),
                len(saved_jobs),
            )

        expired_count = self.repository.mark_expired() if mark_expired else 0
        finished_at = datetime.now(UTC)
        active_jobs_after = len(self.repository.list_job_dicts())

        return IngestionBatchSummary(
            status="completed",
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
