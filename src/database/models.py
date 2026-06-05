"""Database models for skill demand and analytics."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Skill(Base):
    """Skill database model."""
    
    __tablename__ = "skills"
    
    id = Column(String, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    # Relationships
    trends = relationship("SkillTrend", back_populates="skill")
    
    def __repr__(self):
        return f"<Skill(name='{self.name}', category='{self.category}')>"


class SkillTrend(Base):
    """Historical skill trend data."""
    
    __tablename__ = "skill_trends"
    
    id = Column(String, primary_key=True)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False, index=True)
    month = Column(DateTime(timezone=True), nullable=False, index=True)
    occurrences = Column(Integer, default=0)
    percentage = Column(Float)
    salary_premium = Column(Float)
    growth_percentage = Column(Float)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    __table_args__ = (
        UniqueConstraint("skill_id", "month", name="unique_skill_month"),
    )
    
    # Relationships
    skill = relationship("Skill", back_populates="trends")
    
    def __repr__(self):
        return f"<SkillTrend(skill_id='{self.skill_id}', month='{self.month}', " \
               f"occurrences={self.occurrences})>"


class SalaryData(Base):
    """Salary statistics by role and location."""
    
    __tablename__ = "salary_data"
    
    id = Column(String, primary_key=True)
    role = Column(String(255), nullable=False, index=True)
    location = Column(String(255), index=True)
    min_salary = Column(Integer)
    max_salary = Column(Integer)
    median_salary = Column(Integer)
    mean_salary = Column(Float)
    std_dev = Column(Float)
    sample_size = Column(Integer, default=0)
    currency = Column(String(10), default="EUR")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    
    def __repr__(self):
        return f"<SalaryData(role='{self.role}', location='{self.location}', " \
               f"median=${self.median_salary})>"


class JobPosting(Base):
    """Job posting data."""
    
    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint("source", "source_posting_id", name="unique_job_source_posting"),
    )
    
    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), index=True)
    country = Column(String(100), default="Germany")
    city = Column(String(120), index=True)
    federal_state = Column(String(120), index=True)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_period = Column(String(50))
    salary_is_estimated = Column(Boolean, default=False)
    salary_confidence = Column(Float)
    job_type = Column(String(50))
    employment_type = Column(String(80), index=True)
    description = Column(String)
    required_skills = Column(String)
    source = Column(String(50), index=True)
    source_posting_id = Column(String(255), index=True)
    url = Column(String)
    application_url = Column(String)
    company_career_url = Column(String)
    remote_status = Column(String(50), index=True)
    role_type = Column(String(120), index=True)
    occupation_group = Column(String(255), index=True)
    experience_level = Column(String(80), index=True)
    source_legal_basis = Column(String)
    ingestion_batch_id = Column(String(120), index=True)
    posted_date = Column(DateTime(timezone=True), index=True)
    posted_at = Column(DateTime(timezone=True), index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    last_seen_at = Column(DateTime(timezone=True), index=True)
    is_expired = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    
    def __repr__(self):
        return f"<JobPosting(title='{self.title}', company='{self.company}')>"
