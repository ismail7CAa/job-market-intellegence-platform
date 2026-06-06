"""Admin CLI for source onboarding visibility."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from src.data_pipeline.source_policy import (
    evaluate_source,
    get_source_registry_entries,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the source registry CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m src.data_pipeline.sources",
        description="Inspect approved, conditional, and blocked job data sources.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Limit output to one source id.",
    )
    parser.add_argument(
        "--approved-only",
        action="store_true",
        help="Show only sources currently allowed by governance.",
    )
    parser.add_argument(
        "--blocked-only",
        action="store_true",
        help="Show only sources currently blocked by governance.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format.",
    )
    return parser


def _selected_entries(args: argparse.Namespace) -> list[dict]:
    """Return registry rows after applying CLI filters."""
    rows = []
    for entry in get_source_registry_entries():
        if args.source and entry.source_id != args.source:
            continue
        decision = evaluate_source(entry.source_id, legal_basis=entry.legal_basis)
        if args.approved_only and not decision.allowed:
            continue
        if args.blocked_only and decision.allowed:
            continue
        rows.append(
            {
                "source": entry.source_id,
                "display_name": entry.display_name,
                "source_type": entry.source_type,
                "allowed": decision.allowed,
                "approval_status": decision.approval_status,
                "can_store_listings": decision.can_store_listings,
                "can_display_listings": decision.can_display_listings,
                "can_link_apply": decision.can_link_apply,
                "requires_contract": entry.requires_contract,
                "required_action": decision.required_action,
            }
        )
    return rows


def _print_table(rows: list[dict]) -> None:
    """Print a compact table for terminal review."""
    print("")
    print("Source onboarding status")
    print("========================")
    if not rows:
        print("No sources matched the requested filters.")
        return

    header = f"{'SOURCE':<20} {'STATUS':<12} {'TYPE':<22} {'STORE':<6} {'DISPLAY':<8} {'APPLY':<6}"
    print(header)
    print("-" * len(header))
    for row in rows:
        status = "allowed" if row["allowed"] else "blocked"
        print(
            f"{row['source']:<20} {status:<12} {row['source_type']:<22} "
            f"{str(row['can_store_listings']):<6} "
            f"{str(row['can_display_listings']):<8} "
            f"{str(row['can_link_apply']):<6}"
        )
        if row["required_action"]:
            print(f"  required_action: {row['required_action']}")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.approved_only and args.blocked_only:
        parser.error("--approved-only and --blocked-only cannot be combined")

    rows = _selected_entries(args)
    if args.format == "json":
        print(json.dumps({"status": "ready", "sources": rows}, indent=2))
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
