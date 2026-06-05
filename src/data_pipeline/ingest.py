"""Admin CLI for repository-backed job ingestion."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from loguru import logger

from config.settings import get_settings
from src.data_pipeline.ingestion_service import IngestionPolicyError, IngestionService
from src.data_pipeline.pipeline import DataPipeline
from src.database import init_database
from src.database.repository import JobPostingRepository


def build_parser() -> argparse.ArgumentParser:
    """Build the ingestion CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m src.data_pipeline.ingest",
        description="Run approved provider ingestion into the job posting repository.",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Provider source id to ingest. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        dest="keywords",
        help="Search keyword to pass to providers. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum jobs to fetch per source.",
    )
    parser.add_argument(
        "--mark-expired",
        action="store_true",
        help="Mark jobs with past expires_at timestamps as expired after ingestion.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run governance, provider fetch, and validation without writing to the repository.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL override. Defaults to DATABASE_URL from settings.",
    )
    return parser


def _print_summary(summary) -> None:
    """Print a concise terminal summary for operators."""
    print("")
    print("Job ingestion summary")
    print("=====================")
    print(f"Status:            {summary.status}")
    print(f"Batch ID:          {summary.ingestion_batch_id}")
    print(f"Sources:           {', '.join(summary.sources)}")
    print(f"Keywords:          {', '.join(summary.keywords) if summary.keywords else '(none)'}")
    print(f"Limit per source:  {summary.limit_per_source}")
    print(f"Fetched:           {summary.fetched_count}")
    print(f"Saved:             {summary.saved_count}")
    print(f"Expired marked:    {summary.expired_count}")
    print(f"Active jobs after: {summary.active_jobs_after}")
    print(f"Duration seconds:  {summary.duration_seconds}")
    print("")
    print("Provider results")
    print("----------------")
    for result in summary.provider_results:
        print(
            f"- {result.source}: fetched={result.fetched_count}, "
            f"saved={result.saved_count}, allowed={result.allowed}"
        )
        if result.legal_basis:
            print(f"  legal_basis: {result.legal_basis}")
        print(f"  result: {result.reason}")


def run(args: argparse.Namespace) -> int:
    """Execute ingestion from parsed CLI arguments."""
    settings = get_settings()
    sources = args.sources or settings.default_sources
    keywords = args.keywords or settings.default_keywords
    limit = args.limit or settings.default_limit_per_source
    database_url = args.database_url or settings.database_url

    database = init_database(database_url)
    database.create_tables()
    session = database.get_session()
    try:
        pipeline = DataPipeline()
        repository = JobPostingRepository(session)
        service = IngestionService(providers=pipeline.providers, repository=repository)
        summary = service.ingest(
            sources=sources,
            keywords=keywords,
            limit_per_source=limit,
            mark_expired=args.mark_expired,
            dry_run=args.dry_run,
        )
        _print_summary(summary)
        return 0
    except IngestionPolicyError as exc:
        print("")
        print("Job ingestion blocked")
        print("=====================")
        for decision in exc.blocked_sources:
            print(f"- {decision.source}: {decision.reason}")
            if decision.required_action:
                print(f"  required_action: {decision.required_action}")
        return 2
    except Exception as exc:  # pragma: no cover - defensive operator path.
        logger.exception("Ingestion CLI failed")
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
        database.close()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
