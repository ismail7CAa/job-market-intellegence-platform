"""Tests for Alembic database migrations."""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.cmd_opts = None
    config.attributes["configure_logger"] = False
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_head_creates_provider_ready_schema(tmp_path):
    """Fresh databases should migrate to the repository-ready job schema."""
    database_url = f"sqlite:///{tmp_path / 'migration_check.db'}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    columns = {column["name"] for column in inspector.get_columns("job_postings")}
    indexes = {index["name"] for index in inspector.get_indexes("job_postings")}
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("job_postings")
    }
    batch_columns = {column["name"] for column in inspector.get_columns("ingestion_batches")}
    batch_indexes = {index["name"] for index in inspector.get_indexes("ingestion_batches")}

    assert {"job_postings", "skills", "skill_trends", "salary_data", "ingestion_batches"}.issubset(table_names)
    assert {
        "source_posting_id",
        "application_url",
        "company_career_url",
        "city",
        "federal_state",
        "country",
        "occupation_group",
        "experience_level",
        "employment_type",
        "salary_period",
        "salary_is_estimated",
        "salary_confidence",
        "posted_at",
        "expires_at",
        "last_seen_at",
        "ingestion_batch_id",
        "is_expired",
        "required_skills",
    }.issubset(columns)
    assert "unique_job_source_posting" in unique_constraints
    assert {
        "idx_job_city",
        "idx_job_role_type",
        "idx_job_source_posting_id",
        "idx_job_ingestion_batch_id",
        "idx_job_is_expired",
    }.issubset(indexes)
    assert {
        "id",
        "source",
        "status",
        "fetched_count",
        "saved_count",
        "expired_count",
        "started_at",
        "finished_at",
        "error_message",
    }.issubset(batch_columns)
    assert {
        "idx_ingestion_batch_status",
        "idx_ingestion_batch_started_at",
    }.issubset(batch_indexes)
    engine.dispose()
