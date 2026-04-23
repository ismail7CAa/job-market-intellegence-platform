"""Database module initialization."""

from .connection import Database, init_database, get_database
from .models import Skill, SkillTrend, SalaryData, JobPosting
from .repository import (
    SkillRepository,
    SkillTrendRepository,
    SalaryRepository,
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
    "SkillRepository",
    "SkillTrendRepository",
    "SalaryRepository",
    "JobPostingRepository",
]
