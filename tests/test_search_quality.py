"""Regression tests for job search relevance and filtering quality."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.services.job_search import JobSearchService
from src.database.models import Base
from src.database.repository import JobPostingRepository


def _search_quality_jobs() -> list[dict]:
    """Small deterministic job set for search quality regressions."""
    return [
        {
            "id": "nurse_title",
            "title": "Nurse",
            "company": "Care GmbH",
            "location": "Berlin, Germany",
            "description": "Patient care and documentation.",
            "salary_min": 42000,
            "salary_max": 54000,
            "salary_is_estimated": False,
            "job_type": "Full-time",
            "required_skills": ["Patient Care", "Documentation"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal seed data for portfolio use.",
            "remote_status": "onsite",
            "role_type": "Healthcare",
            "occupation_group": "Healthcare and Nursing",
            "experience_level": "mid",
            "employment_type": "permanent",
            "url": "https://example.com/nurse",
        },
        {
            "id": "nurse_description",
            "title": "Hospital Support Worker",
            "company": "Care GmbH",
            "location": "Berlin, Germany",
            "description": "Support nurse teams with daily care routines.",
            "salary_min": 33000,
            "salary_max": 39000,
            "salary_is_estimated": False,
            "job_type": "Full-time",
            "required_skills": ["Patient Care"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal seed data for portfolio use.",
            "remote_status": "onsite",
            "role_type": "Healthcare",
            "occupation_group": "Healthcare and Nursing",
            "experience_level": "entry",
            "employment_type": "permanent",
            "url": "https://example.com/support",
        },
        {
            "id": "care_estimated",
            "title": "Care Coordinator",
            "company": "Care GmbH",
            "location": "Berlin, Germany",
            "description": "Coordinate patient care plans.",
            "salary_min": None,
            "salary_max": None,
            "salary_is_estimated": False,
            "job_type": "Full-time",
            "required_skills": ["Patient Care", "Documentation"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal seed data for portfolio use.",
            "remote_status": "onsite",
            "role_type": "Healthcare",
            "occupation_group": "Healthcare and Nursing",
            "experience_level": "mid",
            "employment_type": "permanent",
            "url": "https://example.com/care-coordinator",
        },
        {
            "id": "accountant",
            "title": "Accountant",
            "company": "Finance GmbH",
            "location": "Frankfurt, Germany",
            "description": "Buchhaltung, reporting, and monthly closing.",
            "salary_min": 50000,
            "salary_max": 68000,
            "salary_is_estimated": False,
            "job_type": "Full-time",
            "required_skills": ["DATEV", "Excel"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal seed data for portfolio use.",
            "remote_status": "hybrid",
            "role_type": "Finance",
            "occupation_group": "Accounting and Finance",
            "experience_level": "mid",
            "employment_type": "permanent",
            "url": "https://example.com/accountant",
        },
    ]


@pytest.fixture
def search_service() -> JobSearchService:
    """Return a service backed by the deterministic regression fixture."""
    return JobSearchService(jobs_loader=_search_quality_jobs)


@pytest.fixture
def repository():
    """Return an isolated repository for active/expired listing tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield JobPostingRepository(session)
    finally:
        session.close()
        engine.dispose()


def test_german_pflege_query_finds_nurse(search_service):
    """German care wording should expand to the Nurse occupation."""
    payload = search_service.build_search_response(query="Pflege", per_page=5)

    assert payload["total"] >= 1
    assert payload["jobs"][0]["id"] == "nurse_title"
    assert any(job["title"] == "Nurse" for job in payload["jobs"])
    assert "ESCO synonym match" in payload["jobs"][0]["match_reasons"]


def test_german_buchhaltung_query_finds_accountant(search_service):
    """German accounting wording should expand to Accountant."""
    payload = search_service.build_search_response(query="Buchhaltung", per_page=5)

    assert payload["total"] >= 1
    assert payload["jobs"][0]["id"] == "accountant"
    assert payload["jobs"][0]["title"] == "Accountant"


def test_exact_title_match_beats_weak_description_match(search_service):
    """Exact title relevance should outrank weak description mentions."""
    payload = search_service.build_search_response(query="Nurse", per_page=5)

    ids = [job["id"] for job in payload["jobs"]]
    assert ids.index("nurse_title") < ids.index("nurse_description")
    assert payload["jobs"][0]["match_reasons"][0] == "title match"
    assert payload["jobs"][0]["relevance_score"] > payload["jobs"][1]["relevance_score"]


def test_salary_filters_keep_listed_and_estimated_salary_types_visible(search_service):
    """Salary filters may include estimates, but the response must mark them clearly."""
    payload = search_service.build_search_response(
        query="care",
        role_type="Healthcare",
        salary_min=45000,
        salary_max=55000,
        per_page=10,
    )

    salary_types = {job["id"]: job["salary_type"] for job in payload["jobs"]}
    assert salary_types["nurse_title"] == "listed"
    assert salary_types["care_estimated"] == "estimated"
    assert payload["summary"]["listed_salary_sample_size"] >= 1
    assert payload["summary"]["estimated_salary_sample_size"] >= 1
    assert all(job["salary_type"] in {"listed", "estimated"} for job in payload["jobs"])


def test_expired_jobs_never_appear_in_search(repository):
    """Repository-backed search should exclude expired listings by default."""
    active_job = {
        **_search_quality_jobs()[0],
        "id": "active_nurse",
        "source_posting_id": "active_nurse",
        "expires_at": datetime.now(UTC) + timedelta(days=7),
    }
    expired_job = {
        **_search_quality_jobs()[0],
        "id": "expired_nurse",
        "source_posting_id": "expired_nurse",
        "title": "Expired Nurse",
        "expires_at": datetime.now(UTC) - timedelta(days=1),
    }
    repository.save_jobs([active_job, expired_job])
    repository.mark_expired(reference_time=datetime.now(UTC))
    service = JobSearchService(
        jobs_loader=lambda: [],
        repository_provider=lambda: repository,
    )

    payload = service.build_search_response(query="Nurse", per_page=10)

    ids = {job["id"] for job in payload["jobs"]}
    assert "active_nurse" in ids
    assert "expired_nurse" not in ids


def test_german_and_english_synonyms_produce_expected_ranking(search_service):
    """German and English occupation aliases should converge on the same top job."""
    german_payload = search_service.build_search_response(query="Pflege", per_page=5)
    english_payload = search_service.build_search_response(query="nursing", per_page=5)

    assert german_payload["jobs"][0]["id"] == "nurse_title"
    assert english_payload["jobs"][0]["id"] == "nurse_title"
    assert german_payload["jobs"][0]["relevance_score"] > 0
    assert english_payload["jobs"][0]["relevance_score"] > 0
