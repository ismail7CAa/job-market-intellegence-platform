"""Configuration settings for Job Market Intelligence Platform."""

import os
from dotenv import load_dotenv

load_dotenv()

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
