"""Database module initialization."""

from .connection import Database, init_database, get_database
from .models import Skill, SkillTrend, SalaryData, JobPosting, IngestionBatch
from .repository import (
    SkillRepository,
    SkillTrendRepository,
    SalaryRepository,
    IngestionBatchRepository,
    JobPostingRepository
)

__all__ = [
    "Database",
    "init_database",
    "get_database",
    "Skill",
    "SkillTrend",
    "SalaryData",
    "JobPosting",
    "IngestionBatch",
    "SkillRepository",
    "SkillTrendRepository",
    "SalaryRepository",
    "IngestionBatchRepository",
    "JobPostingRepository",
]
