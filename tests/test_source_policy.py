"""Tests for legal source governance."""

from src.data_pipeline.source_policy import (
    evaluate_source,
    get_source_registry_entries,
)


def test_commercial_job_boards_are_blocked_without_approved_access():
    """LinkedIn and StepStone-style sources need official/approved access first."""
    for source in ["linkedin", "stepstone", "indeed", "glassdoor"]:
        decision = evaluate_source(source)

        assert decision.allowed is False
        assert decision.reason == "Source is not approved for production ingestion."
        assert "official partner/API access" in decision.required_action
        assert decision.approval_status == "blocked_pending_official_access"
        assert decision.can_store_listings is False


def test_company_feeds_and_licensed_providers_are_approved_sources():
    """The preferred real-source path should remain explicitly approved."""
    for source in ["company_feed", "licensed_provider", "official_api"]:
        decision = evaluate_source(source)

        assert decision.allowed is True
        assert decision.can_store_listings is True
        assert decision.can_display_listings is True
        assert decision.can_link_apply is True


def test_source_registry_lists_preferred_and_blocked_sources():
    """Source onboarding should be visible as configured data, not hardcoded only."""
    entries = {entry.source_id: entry for entry in get_source_registry_entries()}

    assert entries["company_feed"].approval_status == "approved_when_permission_explicit"
    assert entries["licensed_provider"].requires_contract is True
    assert entries["stepstone"].allowed is False
    assert entries["scraper"].approval_status == "blocked"


def test_unknown_source_can_still_be_allowed_by_explicit_legal_basis():
    """Custom future sources can pass only when a legal basis is attached."""
    decision = evaluate_source(
        "regional_employer_feed",
        legal_basis="Company feed with explicit permission from employer.",
    )

    assert decision.allowed is True
    assert decision.approval_status == "approved_by_legal_basis"
