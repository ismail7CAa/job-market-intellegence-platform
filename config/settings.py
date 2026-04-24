"""Configuration settings for Job Market Intelligence Platform."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at runtime in lean environments
    def load_dotenv():
        """Fallback no-op when python-dotenv is unavailable."""
        return False

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/job_market")

# Data Sources
LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY", "")
KAGGLE_API_KEY = os.getenv("KAGGLE_API_KEY", "")

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# NLP Model
NLP_MODEL = os.getenv("NLP_MODEL", "bert-base-uncased")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# MLflow
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    f"sqlite:///{(BASE_DIR / 'mlflow.db').resolve()}"
)
MLFLOW_ARTIFACT_ROOT = os.getenv(
    "MLFLOW_ARTIFACT_ROOT",
    (BASE_DIR / "mlartifacts").resolve().as_uri()
)
MLFLOW_EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "job-market-role-prediction"
)
MLFLOW_REGISTERED_MODEL_NAME = os.getenv(
    "MLFLOW_REGISTERED_MODEL_NAME",
    "job_market_role_predictor"
)
