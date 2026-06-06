"""Deployment configuration validation tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from config.settings import AppSettings


def valid_deployment_settings_kwargs(tmp_path: Path) -> dict:
    """Return a strict deployment config that should pass startup validation."""
    production_data_path = tmp_path / "job_postings_production.csv"
    training_data_path = tmp_path / "job_postings_training.csv"
    production_data_path.write_text("id,title\n", encoding="utf-8")
    training_data_path.write_text("id,title\n", encoding="utf-8")

    return {
        "DEBUG": False,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'job_market.db'}",
        "CORS_ALLOW_ORIGINS": ["https://jobs.example.com"],
        "INGESTION_ENABLED": True,
        "INGESTION_API_TOKEN": "strong-admin-token",
        "RATE_LIMIT_REQUESTS": 600,
        "RATE_LIMIT_WINDOW_SECONDS": 60,
        "PRODUCTION_DATA_PATH": production_data_path,
        "TRAINING_DATA_PATH": training_data_path,
    }


def test_valid_deployment_settings_pass(tmp_path: Path) -> None:
    settings = AppSettings(**valid_deployment_settings_kwargs(tmp_path))

    assert settings.debug is False
    assert settings.ingestion_enabled is True
    assert settings.production_data_path.exists()


def test_rejects_wildcard_cors_when_not_debug(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["CORS_ALLOW_ORIGINS"] = ["*"]

    with pytest.raises(ValidationError, match="CORS_ALLOW_ORIGINS cannot include"):
        AppSettings(**kwargs)


def test_rejects_missing_ingestion_token_when_ingestion_enabled(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["INGESTION_API_TOKEN"] = ""

    with pytest.raises(ValidationError, match="INGESTION_API_TOKEN is required"):
        AppSettings(**kwargs)


def test_rejects_unsupported_database_driver(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["DATABASE_URL"] = "mysql://user:password@localhost/job_market"

    with pytest.raises(ValidationError, match="DATABASE_URL must use sqlite or PostgreSQL"):
        AppSettings(**kwargs)


def test_rejects_malformed_database_url(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["DATABASE_URL"] = "not a database url"

    with pytest.raises(ValidationError, match="DATABASE_URL must be a valid"):
        AppSettings(**kwargs)


def test_rejects_non_positive_rate_limit_values(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["RATE_LIMIT_REQUESTS"] = 0

    with pytest.raises(ValidationError, match="RATE_LIMIT_REQUESTS must be at least 1"):
        AppSettings(**kwargs)


def test_rejects_weak_deployment_rate_limit(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["RATE_LIMIT_REQUESTS"] = 10_000

    with pytest.raises(ValidationError, match="RATE_LIMIT_REQUESTS is too permissive"):
        AppSettings(**kwargs)


def test_rejects_too_short_deployment_rate_limit_window(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["RATE_LIMIT_WINDOW_SECONDS"] = 5

    with pytest.raises(ValidationError, match="RATE_LIMIT_WINDOW_SECONDS must be at least 10"):
        AppSettings(**kwargs)


def test_rejects_missing_production_data_path_when_not_debug(tmp_path: Path) -> None:
    kwargs = valid_deployment_settings_kwargs(tmp_path)
    kwargs["PRODUCTION_DATA_PATH"] = tmp_path / "missing.csv"

    with pytest.raises(ValidationError, match="PRODUCTION_DATA_PATH must point to an existing file"):
        AppSettings(**kwargs)
