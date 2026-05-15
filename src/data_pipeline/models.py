"""Data models for job postings and market data."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """Job posting data model."""
    
    id: str
    title: str
    company: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = "EUR"
    job_type: str  # Full-time, Part-time, Contract, etc.
    description: str
    required_skills: List[str] = Field(default_factory=list)
    posted_date: datetime
    source: str  # "linkedin", "kaggle", etc.
    url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "job_001",
                "title": "Senior Python Developer",
                "company": "Berlin Analytics GmbH",
                "location": "Berlin, Germany",
                "salary_min": 70000,
                "salary_max": 95000,
                "currency": "EUR",
                "job_type": "Full-time",
                "description": "Looking for experienced Python developers...",
                "required_skills": ["Python", "FastAPI", "Docker"],
                "posted_date": "2026-04-23T10:00:00",
                "source": "linkedin",
            }
        }


class SkillDemandData(BaseModel):
    """Skill demand tracking data."""
    
    skill: str
    occurrences: int = 0
    trend: float = 0.0  # Month-over-month growth percentage
    salary_premium: Optional[float] = None  # % higher salary when skill required
    related_skills: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class SalaryData(BaseModel):
    """Salary statistics by role and location."""
    
    role: str
    location: str
    min_salary: float
    max_salary: float
    median_salary: float
    sample_size: int
    currency: str = "EUR"
    last_updated: datetime = Field(default_factory=datetime.now)


class MarketForecast(BaseModel):
    """Predicted job market trends."""
    
    role: str
    confidence_score: float  # 0-1
    predicted_growth: float  # Month-over-month %
    forecast_date: datetime
    factors: List[str] = Field(default_factory=list)
