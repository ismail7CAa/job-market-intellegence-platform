"""Tests for API endpoints backed by local sample data."""

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")

from src.api.main import app


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

    def test_search_facets_endpoint_returns_filter_values(self):
        """Facets endpoint should expose filters for the results UI."""
        response = client.get("/jobs/search/facets")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["total_jobs"] > 0
        assert {"value": "Berlin, Germany", "count": 3} in payload["locations"]
        assert {"value": "Healthcare", "count": 1} in payload["role_types"]
        assert payload["salary_range"]["currency"] == "EUR"

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

    def test_data_fetch_blocks_unapproved_live_sources(self):
        """Live fetch should not silently use unapproved scraping/mock sources."""
        response = client.post(
            "/data/fetch",
            params={"sources": ["linkedin"], "keywords": ["Nurse"], "limit": 10},
        )

        assert response.status_code == 403
        payload = response.json()
        assert payload["detail"]["message"] == "Live ingestion blocked by data-source governance."
        assert payload["detail"]["blocked_sources"][0]["source"] == "linkedin"

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

        assert "JobSearchResponse" in payload["components"]["schemas"]
        assert "JobDetailResponse" in payload["components"]["schemas"]
        assert "ApplyHandoff" in payload["components"]["schemas"]
        assert (
            payload["paths"]["/jobs/search"]["get"]["responses"]["200"]["content"]
            ["application/json"]["schema"]["$ref"]
            == "#/components/schemas/JobSearchResponse"
        )

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
