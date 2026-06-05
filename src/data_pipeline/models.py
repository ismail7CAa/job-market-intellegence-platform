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
    salary_period: Optional[str] = None  # yearly, monthly, hourly
    salary_is_estimated: bool = False
    salary_confidence: Optional[float] = None  # 0-1 confidence for estimated/listed salary quality
    job_type: str  # Full-time, Part-time, Contract, etc.
    employment_type: Optional[str] = None  # permanent, temporary, apprenticeship, internship
    description: str
    required_skills: List[str] = Field(default_factory=list)
    posted_date: datetime
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    is_expired: bool = False
    source: str  # "linkedin", "kaggle", etc.
    source_posting_id: Optional[str] = None
    url: Optional[str] = None
    application_url: Optional[str] = None
    company_career_url: Optional[str] = None
    country: str = "Germany"
    city: Optional[str] = None
    federal_state: Optional[str] = None
    remote_status: Optional[str] = None  # remote, hybrid, onsite
    role_type: Optional[str] = None  # Healthcare, Logistics, Sales, etc.
    occupation_group: Optional[str] = None
    experience_level: Optional[str] = None
    source_legal_basis: Optional[str] = None
    ingestion_batch_id: Optional[str] = None
    
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
                "salary_period": "yearly",
                "salary_is_estimated": False,
                "salary_confidence": 1.0,
                "job_type": "Full-time",
                "employment_type": "permanent",
                "description": "Looking for experienced Python developers...",
                "required_skills": ["Python", "FastAPI", "Docker"],
                "posted_date": "2026-04-23T10:00:00",
                "posted_at": "2026-04-23T10:00:00",
                "last_seen_at": "2026-04-23T10:00:00",
                "is_expired": False,
                "source": "licensed_demo_csv",
                "source_posting_id": "provider_123",
                "application_url": "https://company.example/jobs/provider_123",
                "company_career_url": "https://company.example/careers",
                "country": "Germany",
                "city": "Berlin",
                "federal_state": "Berlin",
                "remote_status": "hybrid",
                "role_type": "Engineering",
                "occupation_group": "Software Engineering",
                "experience_level": "senior",
                "source_legal_basis": "Demo data or licensed provider contract",
                "ingestion_batch_id": "batch_20260423",
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
