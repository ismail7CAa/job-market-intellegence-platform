"""Data-source governance rules for German job market ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


APPROVED_SOURCE_IDS = {
    "legal_demo_csv",
    "local_csv",
    "licensed_provider",
    "company_feed",
    "official_api",
}

BLOCKED_SOURCE_IDS = {
    "linkedin",
    "kaggle",
    "scraper",
    "web_scraping",
    "unapproved_api",
}

APPROVED_LEGAL_BASIS_TERMS = (
    "local legal demo",
    "licensed",
    "official api",
    "company feed",
    "explicit permission",
    "provider contract",
)


@dataclass(frozen=True)
class SourcePolicyDecision:
    """Result of evaluating whether a job-data source may be used."""

    source: str
    allowed: bool
    reason: str
    required_action: str | None = None


def evaluate_source(source: str, legal_basis: str | None = None) -> SourcePolicyDecision:
    """Return whether a source is approved for ingestion or serving."""
    normalized_source = (source or "").strip().lower()
    normalized_basis = (legal_basis or "").strip().lower()

    if normalized_source in APPROVED_SOURCE_IDS:
        return SourcePolicyDecision(
            source=source,
            allowed=True,
            reason="Source is on the approved ingestion list.",
        )

    if normalized_source in BLOCKED_SOURCE_IDS:
        return SourcePolicyDecision(
            source=source,
            allowed=False,
            reason="Source is not approved for production ingestion.",
            required_action=(
                "Use an official API, a licensed provider contract, a company feed with "
                "explicit permission, or the local legal demo dataset."
            ),
        )

    if any(term in normalized_basis for term in APPROVED_LEGAL_BASIS_TERMS):
        return SourcePolicyDecision(
            source=source,
            allowed=True,
            reason="Source includes an acceptable legal basis.",
        )

    return SourcePolicyDecision(
        source=source,
        allowed=False,
        reason="Source has no approved legal basis attached.",
        required_action="Attach source_legal_basis before ingestion or serving.",
    )


def evaluate_sources(sources: Iterable[str]) -> list[SourcePolicyDecision]:
    """Evaluate a collection of source identifiers."""
    return [evaluate_source(source) for source in sources]


def require_approved_sources(sources: Iterable[str]) -> None:
    """Raise ValueError when any source is not approved."""
    decisions = evaluate_sources(sources)
    blocked = [decision for decision in decisions if not decision.allowed]
    if blocked:
        details = "; ".join(
            f"{decision.source}: {decision.reason}" for decision in blocked
        )
        raise ValueError(f"Unapproved data source requested: {details}")
