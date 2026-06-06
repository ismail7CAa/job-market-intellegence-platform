"""Tests for legal source governance."""

from src.data_pipeline.source_policy import evaluate_source


def test_commercial_job_boards_are_blocked_without_approved_access():
    """LinkedIn and StepStone-style sources need official/approved access first."""
    for source in ["linkedin", "stepstone", "indeed", "glassdoor"]:
        decision = evaluate_source(source)

        assert decision.allowed is False
        assert decision.reason == "Source is not approved for production ingestion."
        assert "official API" in decision.required_action


def test_company_feeds_and_licensed_providers_are_approved_sources():
    """The preferred real-source path should remain explicitly approved."""
    for source in ["company_feed", "licensed_provider", "official_api"]:
        decision = evaluate_source(source)

        assert decision.allowed is True
