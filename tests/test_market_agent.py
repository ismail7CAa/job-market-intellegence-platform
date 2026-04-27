"""Tests for the grounded market intelligence agent."""

from src.nlp.market_agent import MarketIntelligenceAgent


def _sample_jobs():
    return [
        {
            "id": "job_normal_1",
            "title": "Data Analyst",
            "company": "Baseline Co",
            "location": "Boston, MA",
            "salary_min": 90000,
            "salary_max": 110000,
        },
        {
            "id": "job_normal_2",
            "title": "Backend Engineer",
            "company": "Build Co",
            "location": "Denver, CO",
            "salary_min": 100000,
            "salary_max": 120000,
        },
        {
            "id": "job_normal_3",
            "title": "Data Engineer",
            "company": "Pipes Co",
            "location": "Austin, TX",
            "salary_min": 105000,
            "salary_max": 125000,
        },
        {
            "id": "job_outlier",
            "title": "Data Scientist",
            "company": "Moonshot AI",
            "location": "Palo Alto, CA",
            "salary_min": 260000,
            "salary_max": 320000,
        },
    ]


def test_agent_explains_flagged_salary_with_evidence():
    """Agent should retrieve anomaly evidence and narrate the salary flag."""
    agent = MarketIntelligenceAgent()

    result = agent.answer(
        question='Why did the model flag salary for "job_outlier" as anomalous?',
        jobs=_sample_jobs(),
    )

    assert result["status"] == "ready"
    assert result["intent"] == "explain_salary_anomaly"
    assert result["evidence"]["job"]["id"] == "job_outlier"
    assert result["evidence"]["anomaly"]["job_id"] == "job_outlier"
    assert "detect_salary_anomalies" in result["tool_trace"]
    assert "flagged because" in result["answer"]


def test_agent_explains_non_flagged_salary():
    """Agent should also explain when a requested job is not anomalous."""
    agent = MarketIntelligenceAgent()

    result = agent.answer(
        question="Why did the model flag this salary as anomalous?",
        jobs=_sample_jobs(),
        job_id="job_normal_2",
    )

    assert result["status"] == "ready"
    assert result["evidence"]["job"]["id"] == "job_normal_2"
    assert result["evidence"]["anomaly"] is None
    assert "was not flagged" in result["answer"]
