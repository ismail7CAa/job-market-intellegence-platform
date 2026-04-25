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
