"""Tests for the job search application service."""

from src.api.services.job_search import JobSearchService


def _jobs():
    return [
        {
            "id": "job_1",
            "title": "Nurse",
            "company": "Care GmbH",
            "location": "Berlin, Germany",
            "description": "Patient care and documentation.",
            "salary_min": 42000,
            "salary_max": 54000,
            "job_type": "Full-time",
            "required_skills": ["Patient Care", "Documentation"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal demo data for portfolio use.",
            "remote_status": "onsite",
            "role_type": "Healthcare",
            "url": "https://example.com/apply/nurse",
        },
        {
            "id": "job_2",
            "title": "Healthcare Assistant",
            "company": "Care GmbH",
            "location": "Berlin, Germany",
            "description": "Support patient care.",
            "salary_min": 32000,
            "salary_max": 40000,
            "job_type": "Full-time",
            "required_skills": ["Patient Care"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal demo data for portfolio use.",
            "remote_status": "onsite",
            "role_type": "Healthcare",
            "url": "https://example.com/apply/assistant",
        },
        {
            "id": "job_3",
            "title": "Accountant",
            "company": "Finance GmbH",
            "location": "Frankfurt, Germany",
            "description": "Financial reporting.",
            "salary_min": 50000,
            "salary_max": 68000,
            "job_type": "Full-time",
            "required_skills": ["DATEV"],
            "source": "legal_demo_csv",
            "source_legal_basis": "Local legal demo data for portfolio use.",
            "remote_status": "hybrid",
            "role_type": "Finance",
            "url": "https://example.com/apply/accountant",
        },
    ]


def test_service_searches_and_formats_results():
    service = JobSearchService(jobs_loader=_jobs)

    payload = service.build_search_response(query="Nurse", location="Berlin")

    assert payload["count"] >= 1
    assert payload["jobs"][0]["id"] == "job_1"
    assert payload["jobs"][0]["salary_label"] == "42,000-54,000 EUR"


def test_service_builds_detail_with_apply_handoff():
    service = JobSearchService(jobs_loader=_jobs)
    job = service.find_job_by_id("job_1")

    detail = service.build_job_detail(job)

    assert detail["application"]["button_label"] == "Apply"
    assert detail["application"]["apply_url"] == "https://example.com/apply/nurse"
    assert detail["market_context"]["same_role_count"] == 2


def test_service_ranks_similar_jobs():
    service = JobSearchService(jobs_loader=_jobs)
    job = service.find_job_by_id("job_1")

    similar = service.build_similar_jobs(job)

    assert similar["count"] == 1
    assert similar["jobs"][0]["id"] == "job_2"


def test_service_facets_include_filter_values():
    service = JobSearchService(jobs_loader=_jobs)

    facets = service.build_search_facets()

    assert facets["total_jobs"] == 3
    assert {"value": "Berlin, Germany", "count": 2} in facets["locations"]
    assert {"value": "Healthcare", "count": 2} in facets["role_types"]
