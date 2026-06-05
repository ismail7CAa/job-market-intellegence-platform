"""Typed configuration for Job Market Intelligence Platform."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at runtime in lean environments
    def load_dotenv() -> bool:
        """Fallback no-op when python-dotenv is unavailable."""
        return False

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_dir: Path = BASE_DIR

    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(BASE_DIR / 'data' / 'job_market.db').resolve()}",
        validation_alias="DATABASE_URL",
    )

    linkedin_api_key: str = Field(default="", validation_alias="LINKEDIN_API_KEY")
    kaggle_api_key: str = Field(default="", validation_alias="KAGGLE_API_KEY")
    kaggle_dataset_id: str = Field(default="", validation_alias="KAGGLE_DATASET_ID")
    kaggle_raw_data_dir: Path = Field(
        default=BASE_DIR / "data" / "raw",
        validation_alias="KAGGLE_RAW_DATA_DIR",
    )

    kafka_bootstrap_servers: str = Field(
        default="",
        validation_alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_topic: str = Field(default="job_postings", validation_alias="KAFKA_TOPIC")
    kafka_consumer_group_id: str = Field(
        default="job_posting_consumers",
        validation_alias="KAFKA_CONSUMER_GROUP_ID",
    )

    bigquery_project: str = Field(default="", validation_alias="BIGQUERY_PROJECT")
    bigquery_dataset: str = Field(default="bronze", validation_alias="BIGQUERY_DATASET")
    bigquery_table: str = Field(
        default="raw_job_postings",
        validation_alias="BIGQUERY_TABLE",
    )

    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    market_region: str = Field(default="Germany", validation_alias="MARKET_REGION")
    default_currency: str = Field(default="EUR", validation_alias="DEFAULT_CURRENCY")
    public_base_url: str = Field(default="http://localhost:8000", validation_alias="PUBLIC_BASE_URL")
    cors_allow_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ],
        validation_alias="CORS_ALLOW_ORIGINS",
    )
    ingestion_api_token: str = Field(default="", validation_alias="INGESTION_API_TOKEN")
    rate_limit_requests: int = Field(default=600, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, validation_alias="RATE_LIMIT_WINDOW_SECONDS")

    nlp_model: str = Field(default="bert-base-uncased", validation_alias="NLP_MODEL")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    default_sources: List[str] = Field(
        default_factory=lambda: ["legal_demo_csv"],
        validation_alias="DEFAULT_SOURCES",
    )
    default_keywords: List[str] = Field(
        default_factory=lambda: [
            "Data Engineer Berlin",
            "Machine Learning Engineer Germany",
            "Cloud Engineer Munich",
        ],
        validation_alias="DEFAULT_KEYWORDS",
    )
    default_limit_per_source: int = Field(default=100, validation_alias="DEFAULT_LIMIT_PER_SOURCE")
    default_jobs_output_path: Path = Field(
        default=BASE_DIR / "data" / "jobs.csv",
        validation_alias="DEFAULT_JOBS_OUTPUT_PATH",
    )
    training_data_path: Path = Field(
        default=BASE_DIR / "data" / "job_postings_training.csv",
        validation_alias="TRAINING_DATA_PATH",
    )
    production_data_path: Path = Field(
        default=BASE_DIR / "data" / "job_postings_production.csv",
        validation_alias="PRODUCTION_DATA_PATH",
    )

    role_predictor_random_state: int = Field(
        default=42,
        validation_alias="ROLE_PREDICTOR_RANDOM_STATE",
    )
    role_predictor_max_iter: int = Field(
        default=1000,
        validation_alias="ROLE_PREDICTOR_MAX_ITER",
    )
    role_demand_growth_per_quarter: float = Field(
        default=0.08,
        validation_alias="ROLE_DEMAND_GROWTH_PER_QUARTER",
    )
    role_prediction_top_n: int = Field(default=10, validation_alias="ROLE_PREDICTION_TOP_N")
    role_predictor_baseline_accuracy: float = Field(
        default=0.8,
        validation_alias="ROLE_PREDICTOR_BASELINE_ACCURACY",
    )
    role_predictor_baseline_f1_macro: float = Field(
        default=0.8,
        validation_alias="ROLE_PREDICTOR_BASELINE_F1_MACRO",
    )

    mlflow_tracking_uri: str = Field(
        default_factory=lambda: f"sqlite:///{(BASE_DIR / 'mlflow.db').resolve()}",
        validation_alias="MLFLOW_TRACKING_URI",
    )
    mlflow_artifact_root: str = Field(
        default_factory=lambda: (BASE_DIR / "mlartifacts").resolve().as_uri(),
        validation_alias="MLFLOW_ARTIFACT_ROOT",
    )
    mlflow_experiment_name: str = Field(
        default="job-market-role-prediction",
        validation_alias="MLFLOW_EXPERIMENT_NAME",
    )
    mlflow_registered_model_name: str = Field(
        default="job_market_role_predictor",
        validation_alias="MLFLOW_REGISTERED_MODEL_NAME",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Accept common deployment labels as falsey debug values."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
        return value


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()


settings = get_settings()

# Compatibility aliases for modules that import constants directly.
DATABASE_URL = settings.database_url
LINKEDIN_API_KEY = settings.linkedin_api_key
KAGGLE_API_KEY = settings.kaggle_api_key
API_HOST = settings.api_host
API_PORT = settings.api_port
DEBUG = settings.debug
NLP_MODEL = settings.nlp_model
LOG_LEVEL = settings.log_level
MARKET_REGION = settings.market_region
DEFAULT_CURRENCY = settings.default_currency
MLFLOW_TRACKING_URI = settings.mlflow_tracking_uri
MLFLOW_ARTIFACT_ROOT = settings.mlflow_artifact_root
MLFLOW_EXPERIMENT_NAME = settings.mlflow_experiment_name
MLFLOW_REGISTERED_MODEL_NAME = settings.mlflow_registered_model_name
