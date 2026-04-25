"""Tests for database models and repositories."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, Skill, SkillTrend, SalaryData, JobPosting
from src.database.repository import (
    SkillRepository, SkillTrendRepository, SalaryRepository, JobPostingRepository
)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestSkillRepository:
    """Test SkillRepository."""
    
    def test_create_skill(self, db_session):
        """Test creating a skill."""
        repo = SkillRepository(db_session)
        skill = repo.create_skill(name="Python", category="Programming Languages")
        
        assert skill.name == "Python"
        assert skill.category == "Programming Languages"
        assert skill.id is not None
    
    def test_get_skill_by_name(self, db_session):
        """Test retrieving skill by name."""
        repo = SkillRepository(db_session)
        repo.create_skill(name="Python")
        
        skill = repo.get_skill_by_name("Python")
        
        assert skill is not None
        assert skill.name == "Python"
    
    def test_get_nonexistent_skill(self, db_session):
        """Test retrieving nonexistent skill."""
        repo = SkillRepository(db_session)
        
        skill = repo.get_skill_by_name("NonExistent")
        
        assert skill is None
    
    def test_get_or_create_skill_existing(self, db_session):
        """Test get_or_create with existing skill."""
        repo = SkillRepository(db_session)
        created = repo.create_skill(name="Python")
        
        retrieved = repo.get_or_create_skill(name="Python")
        
        assert retrieved.id == created.id
    
    def test_get_or_create_skill_new(self, db_session):
        """Test get_or_create with new skill."""
        repo = SkillRepository(db_session)
        
        skill = repo.get_or_create_skill(name="Java", category="Languages")
        
        assert skill.name == "Java"
        assert skill.id is not None
    
    def test_get_all_skills(self, db_session):
        """Test retrieving all skills."""
        repo = SkillRepository(db_session)
        repo.create_skill("Python")
        repo.create_skill("Java")
        repo.create_skill("Go")
        
        skills = repo.get_all_skills()
        
        assert len(skills) == 3


class TestSkillTrendRepository:
    """Test SkillTrendRepository."""
    
    def test_create_trend(self, db_session):
        """Test creating a skill trend."""
        # Create skill first
        skill_repo = SkillRepository(db_session)
        skill = skill_repo.create_skill("Python")
        
        # Create trend
        trend_repo = SkillTrendRepository(db_session)
        trend = trend_repo.create_trend(
            skill_id=skill.id,
            month=datetime(2026, 4, 1, tzinfo=UTC),
            occurrences=100,
            percentage=5.2,
            salary_premium=15.3
        )
        
        assert trend.skill_id == skill.id
        assert trend.occurrences == 100
    
    def test_get_trend_by_skill_and_month(self, db_session):
        """Test retrieving trend by skill and month."""
        skill_repo = SkillRepository(db_session)
        skill = skill_repo.create_skill("Python")
        
        trend_repo = SkillTrendRepository(db_session)
        created_trend = trend_repo.create_trend(
            skill_id=skill.id,
            month=datetime(2026, 4, 1, tzinfo=UTC),
            occurrences=100
        )
        
        retrieved_trend = trend_repo.get_trend_by_skill_and_month(
            skill_id=skill.id,
            month=datetime(2026, 4, 1, tzinfo=UTC)
        )
        
        assert retrieved_trend.id == created_trend.id


class TestSalaryRepository:
    """Test SalaryRepository."""
    
    def test_create_salary_data(self, db_session):
        """Test creating salary data."""
        repo = SalaryRepository(db_session)
        salary = repo.create_salary_data(
            role="Python Developer",
            location="San Francisco",
            min_salary=100000,
            max_salary=180000,
            median_salary=140000,
            sample_size=50
        )
        
        assert salary.role == "Python Developer"
        assert salary.median_salary == 140000
    
    def test_get_salary_by_role_location(self, db_session):
        """Test retrieving salary by role and location."""
        repo = SalaryRepository(db_session)
        repo.create_salary_data(
            role="Data Scientist",
            location="New York",
            min_salary=120000,
            max_salary=200000,
            median_salary=160000,
            sample_size=30
        )
        
        salary = repo.get_salary_by_role_location(
            role="Data Scientist",
            location="New York"
        )
        
        assert salary is not None
        assert salary.role == "Data Scientist"
    
    def test_get_top_paid_roles(self, db_session):
        """Test retrieving top paid roles."""
        repo = SalaryRepository(db_session)
        repo.create_salary_data("Role1", "NYC", 80000, 120000, 100000, 20)
        repo.create_salary_data("Role2", "NYC", 150000, 250000, 200000, 15)
        repo.create_salary_data("Role3", "NYC", 100000, 180000, 140000, 25)
        
        top = repo.get_top_paid_roles(location="NYC", limit=2)
        
        assert len(top) == 2
        assert top[0].median_salary >= top[1].median_salary


class TestJobPostingRepository:
    """Test JobPostingRepository."""
    
    def test_create_job(self, db_session):
        """Test creating a job posting."""
        repo = JobPostingRepository(db_session)
        job = repo.create_job(
            title="Python Developer",
            company="TechCorp",
            location="San Francisco",
            salary_min=100000,
            salary_max=150000
        )
        
        assert job.title == "Python Developer"
        assert job.company == "TechCorp"
    
    def test_get_recent_jobs(self, db_session):
        """Test retrieving recent jobs."""
        repo = JobPostingRepository(db_session)
        repo.create_job("Job1", "Corp", "City", posted_date=datetime.now(UTC))
        repo.create_job("Job2", "Corp", "City", posted_date=datetime.now(UTC))
        
        jobs = repo.get_recent_jobs(days=30, limit=10)
        
        assert len(jobs) == 2
    
    def test_get_jobs_by_title(self, db_session):
        """Test searching jobs by title."""
        repo = JobPostingRepository(db_session)
        repo.create_job("Python Developer", "Corp", "City")
        repo.create_job("Python Engineer", "Corp", "City")
        repo.create_job("Java Developer", "Corp", "City")
        
        jobs = repo.get_jobs_by_title("Python")
        
        assert len(jobs) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
