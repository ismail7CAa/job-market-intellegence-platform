"""Database models for skill demand and analytics."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Skill(Base):
    """Skill database model."""
    
    __tablename__ = "skills"
    
    id = Column(String, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trends = relationship("SkillTrend", back_populates="skill")
    
    def __repr__(self):
        return f"<Skill(name='{self.name}', category='{self.category}')>"


class SkillTrend(Base):
    """Historical skill trend data."""
    
    __tablename__ = "skill_trends"
    
    id = Column(String, primary_key=True)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False, index=True)
    month = Column(DateTime, nullable=False, index=True)
    occurrences = Column(Integer, default=0)
    percentage = Column(Float)
    salary_premium = Column(Float)
    growth_percentage = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    currency = Column(String(10), default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SalaryData(role='{self.role}', location='{self.location}', " \
               f"median=${self.median_salary})>"


class JobPosting(Base):
    """Job posting data."""
    
    __tablename__ = "job_postings"
    
    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), index=True)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    job_type = Column(String(50))
    description = Column(String)
    source = Column(String(50), index=True)
    url = Column(String)
    posted_date = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<JobPosting(title='{self.title}', company='{self.company}')>"
