"""Tests for repository-backed ingestion orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data_pipeline.ingestion_service import IngestionPolicyError, IngestionService
from src.data_pipeline.models import JobPosting
from src.data_pipeline.providers import JobSearchRequest
from src.database.models import Base
from src.database.repository import JobPostingRepository


@pytest.fixture
def job_repository():
    """Create an isolated repository for ingestion tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield JobPostingRepository(session)
    finally:
        session.close()


class FakeProvider:
    """Small provider fixture that returns controlled JobPosting records."""

    source_id = "licensed_provider"
    legal_basis = "Licensed provider contract for tests."

    def __init__(self, jobs: list[JobPosting]):
        self.jobs = jobs

    def fetch(self, request: JobSearchRequest) -> list[JobPosting]:
        return self.jobs[: request.limit]


class BlockedProvider(FakeProvider):
    """Provider fixture that fails source governance."""

    source_id = "linkedin"
    legal_basis = "Unapproved scraping source."


def _job(
    job_id: str,
    source_posting_id: str,
    title: str = "Nurse",
    expires_at: datetime | None = None,
) -> JobPosting:
    return JobPosting(
        id=job_id,
        source="licensed_provider",
        source_posting_id=source_posting_id,
        title=title,
        company="Care GmbH",
        location="Berlin, Germany",
        city="Berlin",
        role_type="Healthcare",
        occupation_group="Healthcare and Nursing",
        job_type="Full-time",
        employment_type="permanent",
        description="Patient care and documentation.",
        required_skills=["Patient Care", "Documentation"],
        posted_date=datetime.now(UTC),
        expires_at=expires_at,
        source_legal_basis="Licensed provider contract for tests.",
    )


def test_ingestion_service_saves_valid_provider_results(job_repository):
    """Approved provider results should validate and persist with a batch id."""
    service = IngestionService(
        providers={"licensed_provider": FakeProvider([_job("job_1", "provider_1")])},
        repository=job_repository,
    )

    summary = service.ingest(
        sources=["licensed_provider"],
        keywords=["Nurse"],
        limit_per_source=10,
        mark_expired=False,
    )

    stored_jobs = job_repository.list_job_dicts()
    assert summary.status == "completed"
    assert summary.fetched_count == 1
    assert summary.saved_count == 1
    assert summary.expired_count == 0
    assert summary.provider_results[0].source == "licensed_provider"
    assert stored_jobs[0]["title"] == "Nurse"
    assert stored_jobs[0]["ingestion_batch_id"] == summary.ingestion_batch_id
    assert stored_jobs[0]["last_seen_at"] is not None


def test_ingestion_service_deduplicates_second_provider_run(job_repository):
    """Repeated provider identities should update the existing repository row."""
    first_service = IngestionService(
        providers={"licensed_provider": FakeProvider([_job("job_1", "provider_1", title="Nurse")])},
        repository=job_repository,
    )
    first_service.ingest(["licensed_provider"], ["Nurse"], mark_expired=False)

    second_service = IngestionService(
        providers={
            "licensed_provider": FakeProvider([
                _job("different_internal_id", "provider_1", title="Senior Nurse")
            ])
        },
        repository=job_repository,
    )
    summary = second_service.ingest(["licensed_provider"], ["Nurse"], mark_expired=False)

    stored_jobs = job_repository.list_job_dicts()
    assert summary.saved_count == 1
    assert len(stored_jobs) == 1
    assert stored_jobs[0]["id"] == "job_1"
    assert stored_jobs[0]["title"] == "Senior Nurse"
    assert stored_jobs[0]["ingestion_batch_id"] == summary.ingestion_batch_id


def test_ingestion_service_blocks_unapproved_provider(job_repository):
    """Source governance should run before fetch or persistence."""
    service = IngestionService(
        providers={"linkedin": BlockedProvider([_job("job_1", "provider_1")])},
        repository=job_repository,
    )

    with pytest.raises(IngestionPolicyError) as exc_info:
        service.ingest(["linkedin"], ["Nurse"])

    assert exc_info.value.blocked_sources[0].source == "linkedin"
    assert job_repository.list_job_dicts() == []


def test_ingestion_service_marks_expired_jobs_after_refresh(job_repository):
    """Refresh batches should be able to expire stale rows after saving new ones."""
    job_repository.save_jobs([
        _job(
            "expired_job",
            "expired_1",
            title="Expired Nurse",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    ])
    service = IngestionService(
        providers={"licensed_provider": FakeProvider([_job("active_job", "active_1")])},
        repository=job_repository,
    )

    summary = service.ingest(["licensed_provider"], ["Nurse"], mark_expired=True)

    assert summary.expired_count == 1
    assert {job["id"] for job in job_repository.list_job_dicts()} == {"active_job"}
    assert job_repository.get_job_dict_by_id("expired_job", include_expired=True)["is_expired"] is True
