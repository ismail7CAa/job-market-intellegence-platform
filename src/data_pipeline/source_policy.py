"""Data-source governance rules for German job market ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


APPROVED_LEGAL_BASIS_TERMS = (
    "local legal demo",
    "local legal seed",
    "licensed",
    "official api",
    "company feed",
    "explicit permission",
    "provider contract",
)


@dataclass(frozen=True)
class SourceRegistryEntry:
    """Configured onboarding status for one possible listing source."""

    source_id: str
    display_name: str
    source_type: str
    allowed: bool
    approval_status: str
    legal_basis: str | None = None
    required_action: str | None = None
    can_store_listings: bool = False
    can_display_listings: bool = False
    can_link_apply: bool = False
    requires_contract: bool = False
    refresh_policy: str | None = None
    dedupe_key: str | None = None
    expiry_policy: str | None = None
    use_case: str | None = None


@dataclass(frozen=True)
class SourcePolicyDecision:
    """Result of evaluating whether a job-data source may be used."""

    source: str
    allowed: bool
    reason: str
    required_action: str | None = None
    approval_status: str | None = None
    source_type: str | None = None
    can_store_listings: bool = False
    can_display_listings: bool = False
    can_link_apply: bool = False


def _registry_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "source_registry.json"


@lru_cache(maxsize=1)
def load_source_registry() -> dict[str, SourceRegistryEntry]:
    """Load configured source onboarding entries from the repository registry."""
    with _registry_path().open(encoding="utf-8") as registry_file:
        raw_entries = json.load(registry_file)

    entries = {}
    for raw_entry in raw_entries:
        entry = SourceRegistryEntry(**raw_entry)
        entries[entry.source_id.lower()] = entry
    return entries


def get_source_registry_entries() -> list[SourceRegistryEntry]:
    """Return source registry entries in configured order."""
    registry = load_source_registry()
    return list(registry.values())


def get_source_registry_entry(source: str) -> SourceRegistryEntry | None:
    """Return the onboarding entry for one source id when configured."""
    return load_source_registry().get((source or "").strip().lower())


APPROVED_SOURCE_IDS = {
    source_id for source_id, entry in load_source_registry().items() if entry.allowed
}

BLOCKED_SOURCE_IDS = {
    source_id for source_id, entry in load_source_registry().items() if not entry.allowed
}


def evaluate_source(source: str, legal_basis: str | None = None) -> SourcePolicyDecision:
    """Return whether a source is approved for ingestion or serving."""
    normalized_source = (source or "").strip().lower()
    normalized_basis = (legal_basis or "").strip().lower()
    registry_entry = get_source_registry_entry(normalized_source)

    if registry_entry is not None:
        if registry_entry.allowed:
            return SourcePolicyDecision(
                source=source,
                allowed=True,
                reason="Source is approved by the source onboarding registry.",
                required_action=registry_entry.required_action,
                approval_status=registry_entry.approval_status,
                source_type=registry_entry.source_type,
                can_store_listings=registry_entry.can_store_listings,
                can_display_listings=registry_entry.can_display_listings,
                can_link_apply=registry_entry.can_link_apply,
            )

        return SourcePolicyDecision(
            source=source,
            allowed=False,
            reason="Source is not approved for production ingestion.",
            required_action=registry_entry.required_action,
            approval_status=registry_entry.approval_status,
            source_type=registry_entry.source_type,
            can_store_listings=registry_entry.can_store_listings,
            can_display_listings=registry_entry.can_display_listings,
            can_link_apply=registry_entry.can_link_apply,
        )

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
                "explicit permission, or the local legal seed listing dataset."
            ),
        )

    if any(term in normalized_basis for term in APPROVED_LEGAL_BASIS_TERMS):
        return SourcePolicyDecision(
            source=source,
            allowed=True,
            reason="Source includes an acceptable legal basis.",
            approval_status="approved_by_legal_basis",
            source_type="custom",
            can_store_listings=True,
            can_display_listings=True,
            can_link_apply=True,
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
