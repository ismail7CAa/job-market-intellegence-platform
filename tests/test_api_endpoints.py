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

    def test_query_endpoint(self):
        """Query endpoint should return a structured answer."""
        response = client.post("/query", params={"question": "What are the top 3 skills?"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["parsed_query"]["intent"] == "top_skills"
        assert "Top skills" in payload["answer"]

    def test_salary_anomalies_endpoint(self):
        """Salary anomaly endpoint should return a stable response shape."""
        response = client.get("/salary/anomalies", params={"role": "Data Scientist"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["role"] == "Data Scientist"
        assert "anomalies" in payload
        assert "salary_range" in payload

    def test_agent_explain_endpoint(self):
        """Agent endpoint should return a grounded salary anomaly explanation."""
        response = client.post(
            "/agent/explain",
            params={
                "question": "Why did the model flag this salary as anomalous?",
                "job_id": "prod_005",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ready"
        assert payload["intent"] == "explain_salary_anomaly"
        assert payload["evidence"]["job"]["id"] == "prod_005"
        assert "tool_trace" in payload
        assert "flagged because" in payload["answer"]
