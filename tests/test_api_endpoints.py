"""Tests for API endpoints backed by local sample data."""

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")

from src.api.main import app
import src.api.main as api_main


client = testclient.TestClient(app)


class TestApiEndpoints:
    """Verify the API placeholder routes now return real results."""

    def test_predict_roles_endpoint(self):
        """Predict roles endpoint should return model-backed output."""
        response = client.get("/predict/roles", params={"quarters_ahead": 2})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["predicted_roles"]
        assert payload["evaluation_metrics"]["accuracy"] >= 0.8

    def test_job_search_endpoint_supports_non_tech_roles(self):
        """Job search should return broader German roles with apply and data-policy context."""
        response = client.get("/jobs/search", params={"q": "Nurse", "location": "Berlin"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["jobs"][0]["title"] == "Nurse"
        assert payload["jobs"][0]["apply_url"].startswith("https://www.arbeitsagentur.de/")
        assert payload["jobs"][0]["apply_endpoint"] == "/jobs/prod_001/apply"
        assert payload["jobs"][0]["salary_type"] == "listed"
        assert payload["jobs"][0]["source_posting_id"] == "seed_prod_001"
        assert payload["jobs"][0]["city"] == "Berlin"
        assert payload["jobs"][0]["federal_state"] == "Berlin"
        assert payload["jobs"][0]["occupation_group"] == "Healthcare and Nursing"
        assert payload["jobs"][0]["experience_level"] == "mid"
        assert payload["jobs"][0]["employment_type"] == "permanent"
        assert payload["jobs"][0]["salary_period"] == "yearly"
        assert payload["jobs"][0]["salary_is_estimated"] is False
        assert payload["jobs"][0]["salary_confidence"] == 1.0
        assert payload["data_governance"]["region"] == "Germany"
        assert "licensed" in payload["data_governance"]["legal_position"]
        assert payload["page"] == 1
        assert payload["per_page"] == 25
        assert payload["total"] >= payload["count"]
        assert payload["sort"] == "relevance"
        assert payload["jobs"][0]["relevance_score"] > 0
        assert payload["jobs"][0]["match_reasons"]

    def test_job_search_supports_filters_pagination_and_sorting(self):
        """Search should behave like a real filtered, paginated engine."""
        response = client.get(
            "/jobs/search",
            params={
                "role_type": "Finance",
                "employment_type": "permanent",
                "salary_min": 50000,
                "salary_max": 80000,
                "sort": "salary_desc",
                "page": 1,
                "per_page": 3,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 3
        assert payload["total"] >= 3
        assert payload["total_pages"] >= 1
        assert payload["filters"]["role_type"] == "Finance"
        assert payload["filters"]["employment_type"] == "permanent"
        assert payload["jobs"][0]["salary_midpoint"] >= payload["jobs"][1]["salary_midpoint"]
        assert all(job["role_type"] == "Finance" for job in payload["jobs"])

    def test_job_search_supports_company_filter(self):
        """Company filter should narrow search results."""
        response = client.get("/jobs/search", params={"company": "Mittelstand Finance", "per_page": 10})

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] >= 1
        assert all("Mittelstand Finance" in job["company"] for job in payload["jobs"])

    def test_job_search_estimates_missing_salary_with_confidence(self):
        """Jobs without listed salaries should receive clearly marked estimates."""
        response = client.get(
            "/jobs/search",
            params={"q": "Radiology Technician", "location": "Frankfurt"},
        )

        assert response.status_code == 200
        payload = response.json()
        job = payload["jobs"][0]
        assert job["id"] == "prod_005"
        assert job["salary_type"] == "estimated"
        assert job["salary_is_estimated"] is True
        assert job["salary_label"].startswith("Estimated ")
        assert job["salary_confidence"] > 0
        assert job["salary_estimation_basis"]
        assert payload["summary"]["estimated_salary_sample_size"] >= 1

    def test_search_facets_endpoint_returns_filter_values(self):
        """Facets endpoint should expose filters for the results UI."""
        response = client.get("/jobs/search/facets")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["total_jobs"] >= 120
        assert {"value": "Berlin, Germany", "count": 10} in payload["locations"]
        assert {"value": "Healthcare", "count": 10} in payload["role_types"]
        assert {"value": "Public Sector", "count": 10} in payload["role_types"]
        assert payload["salary_range"]["currency"] == "EUR"

    def test_job_search_uses_esco_query_expansion(self):
        """Search should understand ESCO occupation aliases."""
        response = client.get("/jobs/search", params={"q": "nursing", "location": "Berlin"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] >= 1
        assert payload["jobs"][0]["title"] == "Nurse"

    def test_esco_normalize_endpoint_returns_market_context(self):
        """ESCO normalization should be exposed as market context, not listings."""
        response = client.get("/market/esco/normalize", params={"q": "Buchhaltung"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_use"] == "market_context_enrichment"
        assert payload["occupations"][0]["preferred_label"] == "Accountant"
        assert "accountant" in payload["expanded_terms"]

    def test_job_detail_endpoint_returns_application_and_market_context(self):
        """Job detail should provide everything needed for a result detail page."""
        response = client.get("/jobs/prod_001")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == "prod_001"
        assert payload["title"] == "Nurse"
        assert payload["application"]["button_label"] == "Apply"
        assert payload["application"]["application_url"].startswith("https://www.arbeitsagentur.de/")
        assert payload["salary"]["type"] == "listed"
        assert payload["market_context"]["similar_jobs_endpoint"] == "/jobs/prod_001/similar"

    def test_similar_jobs_endpoint_returns_related_jobs(self):
        """Similar jobs should return related postings without the selected job."""
        response = client.get("/jobs/prod_003/similar", params={"limit": 3})

        assert response.status_code == 200
        payload = response.json()
        assert payload["job_id"] == "prod_003"
        assert payload["count"] >= 1
        assert all(job["id"] != "prod_003" for job in payload["jobs"])

    def test_apply_handoff_endpoint_returns_application_target(self):
        """Apply handoff should expose one clear application target for a job."""
        response = client.get("/jobs/prod_001/apply", params={"redirect": False})

        assert response.status_code == 200
        payload = response.json()
        assert payload["job_id"] == "prod_001"
        assert payload["button_label"] == "Apply"
        assert payload["apply_method"] == "external_redirect"
        assert payload["source_allowed"] is True
        assert payload["apply_url"].startswith("https://www.arbeitsagentur.de/")

    def test_apply_handoff_redirects_to_apply_url(self):
        """Apply redirect should send users straight to the legal apply/source page."""
        response = client.get("/jobs/prod_001/apply", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"].startswith("https://www.arbeitsagentur.de/")

    def test_data_governance_endpoint_reports_approved_demo_data(self):
        """Governance endpoint should expose legal-source status."""
        response = client.get("/data/governance")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["approved_for_current_stage"] is True
        assert payload["sources"][0]["allowed"] is True

    def test_data_fetch_is_hidden_without_admin_token(self):
        """Live fetch should not be discoverable or usable as a public route."""
        response = client.post(
            "/data/fetch",
            params={"sources": ["legal_demo_csv"], "keywords": ["Nurse"], "limit": 10},
        )

        assert response.status_code == 404

    def test_data_fetch_with_admin_token_still_enforces_source_governance(self, monkeypatch):
        """Protected live fetch should still block unapproved scraping/mock sources."""
        monkeypatch.setattr(api_main.settings, "ingestion_api_token", "secret-token")

        response = client.post(
            "/data/fetch",
            params={"sources": ["linkedin"], "keywords": ["Nurse"], "limit": 10},
            headers={"X-Admin-Token": "secret-token"},
        )

        assert response.status_code == 403
        payload = response.json()
        assert payload["error"] == "source_policy_violation"
        assert payload["message"] == "Live ingestion blocked by data-source governance."
        assert payload["details"]["blocked_sources"][0]["source"] == "linkedin"

    def test_data_fetch_with_admin_token_uses_repository_ingestion(self, monkeypatch):
        """Protected fetch should return a repository-backed ingestion batch summary."""
        monkeypatch.setattr(api_main.settings, "ingestion_api_token", "secret-token")

        response = client.post(
            "/data/fetch",
            params={"sources": ["legal_demo_csv"], "keywords": ["Nurse"], "limit": 10},
            headers={"X-Admin-Token": "secret-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["ingestion_batch_id"].startswith("ing_")
        assert payload["sources"] == ["legal_demo_csv"]
        assert payload["fetched_count"] >= 1
        assert payload["saved_count"] == payload["fetched_count"]
        assert payload["active_jobs_after"] >= 120
        assert payload["provider_results"][0]["source"] == "legal_demo_csv"

    def test_data_fetch_reports_repository_unavailable(self, monkeypatch):
        """Protected fetch should standardize repository availability failures."""
        monkeypatch.setattr(api_main.settings, "ingestion_api_token", "secret-token")
        monkeypatch.setattr(api_main, "_job_repository", None)

        response = client.post(
            "/data/fetch",
            params={"sources": ["legal_demo_csv"], "keywords": ["Nurse"], "limit": 10},
            headers={"X-Admin-Token": "secret-token"},
        )

        assert response.status_code == 503
        assert response.json() == {
            "error": "repository_unavailable",
            "message": "Job repository is not available.",
            "details": {},
        }

    def test_engine_workflow_endpoint_documents_search_process(self):
        """Workflow endpoint should describe the platform engine steps."""
        response = client.get("/engine/workflow")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["workflow"][0]["step"] == "Search intent"
        assert any(step["step"] == "Apply handoff" for step in payload["workflow"])

    def test_openapi_exposes_explicit_job_response_schemas(self):
        """OpenAPI should document concrete job response models."""
        payload = client.get("/openapi.json").json()

        assert "/data/fetch" not in payload["paths"]
        assert "JobSearchResponse" in payload["components"]["schemas"]
        assert "JobDetailResponse" in payload["components"]["schemas"]
        assert "ApplyHandoff" in payload["components"]["schemas"]
        assert "ErrorResponse" in payload["components"]["schemas"]
        assert (
            payload["paths"]["/jobs/search"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"]["$ref"]
            == "#/components/schemas/JobSearchResponse"
        )
        assert "SearchFilters" in payload["components"]["schemas"]

    def test_salary_anomalies_endpoint(self):
        """Salary anomaly endpoint should return a stable response shape."""
        response = client.get("/salary/anomalies", params={"role": "Data Scientist"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["role"] == "Data Scientist"
        assert "anomalies" in payload
        assert "salary_range" in payload

    def test_agent_routes_are_not_public_backend_surface(self):
        """The product backend should not expose the old agent routes."""
        assert client.post("/query", params={"question": "What are the top skills?"}).status_code == 404
        assert client.post("/agent/explain", params={"question": "Why?", "job_id": "prod_005"}).status_code == 404

    def test_health_and_readiness_are_distinct(self):
        """Liveness should be cheap while readiness checks dependencies."""
        health = client.get("/health")
        ready = client.get("/ready")

        assert health.status_code == 200
        assert health.json()["status"] == "healthy"
        assert "database" not in health.json()
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"
        assert ready.json()["database"] == "connected"
        assert ready.json()["data"] == "loaded"
        assert ready.json()["job_count"] >= 120

    def test_rate_limiting_rejects_excess_public_requests(self, monkeypatch):
        """Public routes should reject bursts over the configured request limit."""
        monkeypatch.setattr(api_main.settings, "rate_limit_requests", 1)
        monkeypatch.setattr(api_main.settings, "rate_limit_window_seconds", 60)
        api_main._rate_limit_buckets.clear()

        headers = {"X-Forwarded-For": "203.0.113.77"}
        first = client.get("/jobs/search", params={"per_page": 1}, headers=headers)
        second = client.get("/jobs/search", params={"per_page": 1}, headers=headers)

        api_main._rate_limit_buckets.clear()
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["x-request-id"]
        assert second.json()["error"] == "rate_limit_exceeded"
        assert second.json()["message"] == "Rate limit exceeded."
        assert second.json()["details"]["request_id"]

    def test_request_id_is_returned_and_can_be_supplied_by_callers(self):
        """Responses should carry a request id for log correlation."""
        response = client.get(
            "/health",
            headers={"X-Request-ID": "test-request-id"},
        )

        assert response.status_code == 200
        assert response.headers["x-request-id"] == "test-request-id"

    def test_unhandled_errors_return_request_id(self, monkeypatch):
        """Error middleware should log context and return the request id."""
        def fail_search(*args, **kwargs):
            raise RuntimeError("forced observability failure")

        monkeypatch.setattr(api_main.job_search_service, "build_search_response", fail_search)

        response = client.get(
            "/jobs/search",
            params={"q": "Nurse"},
            headers={"X-Request-ID": "error-request-id"},
        )

        assert response.status_code == 500
        assert response.headers["x-request-id"] == "error-request-id"
        assert response.json() == {
            "error": "internal_error",
            "message": "Internal server error.",
            "details": {"request_id": "error-request-id"},
        }

    def test_missing_job_uses_standard_error_contract(self):
        """Missing job lookups should use the stable frontend error shape."""
        response = client.get("/jobs/not-a-real-job")

        assert response.status_code == 404
        assert response.json() == {
            "error": "job_not_found",
            "message": "Job 'not-a-real-job' not found.",
            "details": {"job_id": "not-a-real-job"},
        }

    def test_request_validation_uses_standard_error_contract(self):
        """Query validation failures should use the stable frontend error shape."""
        response = client.get("/jobs/search", params={"page": 0})

        assert response.status_code == 422
        payload = response.json()
        assert payload["error"] == "validation_failed"
        assert payload["message"] == "Request validation failed."
        assert payload["details"]["errors"]
