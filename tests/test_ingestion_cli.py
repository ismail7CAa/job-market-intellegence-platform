"""Tests for the admin ingestion CLI."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data_pipeline.ingest import main
from src.database.models import Base
from src.database.repository import JobPostingRepository


def _database_url(tmp_path):
    return f"sqlite:///{tmp_path / 'ingestion_cli.db'}"


def _count_jobs(database_url: str) -> int:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        return len(JobPostingRepository(session).list_job_dicts())
    finally:
        session.close()
        engine.dispose()


def test_ingestion_cli_dry_run_does_not_persist_jobs(tmp_path, capsys):
    """Dry run should fetch and validate without writing repository rows."""
    database_url = _database_url(tmp_path)

    exit_code = main([
        "--source",
        "legal_demo_csv",
        "--keyword",
        "Nurse",
        "--limit",
        "5",
        "--dry-run",
        "--database-url",
        database_url,
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Job ingestion summary" in output
    assert "Status:            dry_run" in output
    assert "Fetched:" in output
    assert "Saved:             0" in output
    assert _count_jobs(database_url) == 0


def test_ingestion_cli_persists_approved_provider_jobs(tmp_path, capsys):
    """Approved ingestion should write provider results to the repository."""
    database_url = _database_url(tmp_path)

    exit_code = main([
        "--source",
        "legal_demo_csv",
        "--keyword",
        "Nurse",
        "--limit",
        "5",
        "--database-url",
        database_url,
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Status:            completed" in output
    assert "legal_demo_csv" in output
    assert _count_jobs(database_url) >= 1


def test_ingestion_cli_reports_blocked_sources(tmp_path, capsys):
    """CLI should return a distinct exit code for source-governance failures."""
    exit_code = main([
        "--source",
        "linkedin",
        "--keyword",
        "Nurse",
        "--database-url",
        _database_url(tmp_path),
    ])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "Job ingestion blocked" in output
    assert "linkedin" in output
