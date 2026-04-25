"""Repository pattern for database operations."""

from datetime import UTC, datetime, timedelta
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .models import Skill, SkillTrend, SalaryData, JobPosting


class SkillRepository:
    """Repository for skill-related database operations."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_skill(self, name: str, category: str = None) -> Skill:
        """Create a new skill.
        
        Args:
            name: Skill name
            category: Skill category
            
        Returns:
            Created Skill object
        """
        skill = Skill(
            id=str(uuid.uuid4()),
            name=name,
            category=category
        )
        self.session.add(skill)
        self.session.commit()
        return skill
    
    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """Get skill by name.
        
        Args:
            name: Skill name
            
        Returns:
            Skill object or None
        """
        return self.session.query(Skill).filter(Skill.name == name).first()
    
    def get_or_create_skill(self, name: str, category: str = None) -> Skill:
        """Get skill by name or create if not exists.
        
        Args:
            name: Skill name
            category: Skill category
            
        Returns:
            Skill object
        """
        skill = self.get_skill_by_name(name)
        if not skill:
            skill = self.create_skill(name, category)
        return skill
    
    def get_all_skills(self) -> List[Skill]:
        """Get all skills from database.
        
        Returns:
            List of Skill objects
        """
        return self.session.query(Skill).all()


class SkillTrendRepository:
    """Repository for skill trend data."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_trend(
        self,
        skill_id: str,
        month: datetime,
        occurrences: int,
        percentage: float = None,
        salary_premium: float = None,
        growth_percentage: float = None
    ) -> SkillTrend:
        """Create a new skill trend record.
        
        Args:
            skill_id: Skill ID
            month: Month date
            occurrences: Number of occurrences
            percentage: Percentage of all skills
            salary_premium: Salary premium percentage
            growth_percentage: Month-over-month growth
            
        Returns:
            Created SkillTrend object
        """
        trend = SkillTrend(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            month=month,
            occurrences=occurrences,
            percentage=percentage,
            salary_premium=salary_premium,
            growth_percentage=growth_percentage
        )
        self.session.add(trend)
        self.session.commit()
        return trend
    
    def get_trend_by_skill_and_month(self, skill_id: str, month: datetime) -> Optional[SkillTrend]:
        """Get trend for specific skill and month.
        
        Args:
            skill_id: Skill ID
            month: Month date
            
        Returns:
            SkillTrend object or None
        """
        return self.session.query(SkillTrend).filter(
            SkillTrend.skill_id == skill_id,
            SkillTrend.month == month
        ).first()
    
    def get_trends_by_skill(self, skill_id: str, limit: int = 12) -> List[SkillTrend]:
        """Get recent trends for a skill.
        
        Args:
            skill_id: Skill ID
            limit: Number of months to retrieve
            
        Returns:
            List of SkillTrend objects
        """
        return self.session.query(SkillTrend).filter(
            SkillTrend.skill_id == skill_id
        ).order_by(desc(SkillTrend.month)).limit(limit).all()
    
    def get_top_trending_skills(self, month: datetime = None, limit: int = 10) -> List[tuple]:
        """Get top skills by occurrences for a month.
        
        Args:
            month: Month date (defaults to latest)
            limit: Number of skills
            
        Returns:
            List of (Skill, SkillTrend) tuples
        """
        if not month:
            # Get latest month with data
            latest = self.session.query(func.max(SkillTrend.month)).scalar()
            month = latest
        
        trends = self.session.query(SkillTrend).filter(
            SkillTrend.month == month
        ).order_by(desc(SkillTrend.occurrences)).limit(limit).all()
        
        return trends


class SalaryRepository:
    """Repository for salary data."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_salary_data(
        self,
        role: str,
        location: str,
        min_salary: int,
        max_salary: int,
        median_salary: int,
        sample_size: int
    ) -> SalaryData:
        """Create salary data record.
        
        Args:
            role: Job role/title
            location: Location
            min_salary: Minimum salary
            max_salary: Maximum salary
            median_salary: Median salary
            sample_size: Number of samples
            
        Returns:
            Created SalaryData object
        """
        salary = SalaryData(
            id=str(uuid.uuid4()),
            role=role,
            location=location,
            min_salary=min_salary,
            max_salary=max_salary,
            median_salary=median_salary,
            mean_salary=(min_salary + max_salary) / 2,
            sample_size=sample_size
        )
        self.session.add(salary)
        self.session.commit()
        return salary
    
    def get_salary_by_role_location(self, role: str, location: str = None) -> Optional[SalaryData]:
        """Get salary data for role and location.
        
        Args:
            role: Job role
            location: Optional location filter
            
        Returns:
            SalaryData object or None
        """
        query = self.session.query(SalaryData).filter(SalaryData.role == role)
        if location:
            query = query.filter(SalaryData.location == location)
        return query.first()
    
    def get_top_paid_roles(self, location: str = None, limit: int = 10) -> List[SalaryData]:
        """Get highest paid roles.
        
        Args:
            location: Optional location filter
            limit: Number of roles
            
        Returns:
            List of SalaryData objects
        """
        query = self.session.query(SalaryData)
        if location:
            query = query.filter(SalaryData.location == location)
        return query.order_by(desc(SalaryData.median_salary)).limit(limit).all()


class JobPostingRepository:
    """Repository for job posting data."""
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create_job(
        self,
        title: str,
        company: str,
        location: str,
        salary_min: int = None,
        salary_max: int = None,
        job_type: str = None,
        description: str = None,
        source: str = None,
        url: str = None,
        posted_date: datetime = None
    ) -> JobPosting:
        """Create a job posting record.
        
        Args:
            title: Job title
            company: Company name
            location: Job location
            salary_min: Minimum salary
            salary_max: Maximum salary
            job_type: Job type (full-time, part-time, etc.)
            description: Job description
            source: Data source (linkedin, kaggle, etc.)
            url: Job URL
            posted_date: When job was posted
            
        Returns:
            Created JobPosting object
        """
        job = JobPosting(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            location=location,
            salary_min=salary_min,
            salary_max=salary_max,
            job_type=job_type,
            description=description,
            source=source,
            url=url,
            posted_date=posted_date or datetime.now(UTC)
        )
        self.session.add(job)
        self.session.commit()
        return job
    
    def get_recent_jobs(self, days: int = 30, limit: int = 100) -> List[JobPosting]:
        """Get recent job postings.
        
        Args:
            days: Get jobs from last N days
            limit: Maximum number of jobs
            
        Returns:
            List of JobPosting objects
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        return self.session.query(JobPosting).filter(
            JobPosting.posted_date >= cutoff_date
        ).order_by(desc(JobPosting.posted_date)).limit(limit).all()
    
    def get_jobs_by_title(self, title: str, limit: int = 50) -> List[JobPosting]:
        """Get jobs by title.
        
        Args:
            title: Job title to search
            limit: Maximum number of jobs
            
        Returns:
            List of JobPosting objects
        """
        return self.session.query(JobPosting).filter(
            JobPosting.title.ilike(f"%{title}%")
        ).limit(limit).all()
    
    def count_jobs_by_location(self) -> List[tuple]:
        """Count jobs by location.
        
        Returns:
            List of (location, count) tuples
        """
        return self.session.query(
            JobPosting.location,
            func.count(JobPosting.id)
        ).group_by(JobPosting.location).all()
