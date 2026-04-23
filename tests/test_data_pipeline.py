"""Tests for the data pipeline."""

import pytest
from datetime import datetime
from src.data_pipeline.models import JobPosting
from src.data_pipeline.scraper import LinkedInScraper, KaggleDataLoader
from src.data_pipeline.pipeline import DataPipeline


class TestJobPostingModel:
    """Test JobPosting data model."""

    def test_create_job_posting(self):
        """Test creating a job posting."""
        job = JobPosting(
            id="job_001",
            title="Python Developer",
            company="Tech Corp",
            location="San Francisco, CA",
            salary_min=100000,
            salary_max=150000,
            job_type="Full-time",
            description="Looking for experienced Python developers",
            required_skills=["Python", "FastAPI"],
            posted_date=datetime.now(),
            source="linkedin"
        )
        
        assert job.id == "job_001"
        assert job.title == "Python Developer"
        assert job.salary_min == 100000
        assert len(job.required_skills) == 2

    def test_job_posting_defaults(self):
        """Test JobPosting with default values."""
        job = JobPosting(
            id="job_002",
            title="Data Scientist",
            company="Data Inc",
            location="New York, NY",
            job_type="Full-time",
            description="Data science role",
            posted_date=datetime.now(),
            source="kaggle"
        )
        
        assert job.salary_min is None
        assert job.currency == "USD"
        assert job.required_skills == []


class TestLinkedInScraper:
    """Test LinkedIn scraper."""

    def test_scraper_initialization(self):
        """Test scraper initialization."""
        scraper = LinkedInScraper(api_key="test_key")
        assert scraper.api_key == "test_key"

    def test_fetch_mock_data(self):
        """Test fetching mock data when API key is not set."""
        scraper = LinkedInScraper()  # No API key
        jobs = scraper.fetch(keyword="Python Developer", limit=5)
        
        assert len(jobs) <= 5
        assert all(isinstance(job, JobPosting) for job in jobs)
        assert all(job.source == "linkedin" for job in jobs)

    def test_skill_extraction(self):
        """Test skill extraction from text."""
        scraper = LinkedInScraper()
        text = "We are looking for a Python developer with FastAPI and Docker experience"
        skills = scraper._extract_skills(text)
        
        assert "Python" in skills
        assert "FastAPI" in skills
        assert "Docker" in skills


class TestKaggleDataLoader:
    """Test Kaggle data loader."""

    def test_loader_initialization(self):
        """Test loader initialization."""
        loader = KaggleDataLoader(dataset_id="test_dataset")
        assert loader.dataset_id == "test_dataset"

    def test_fetch_mock_data(self):
        """Test fetching mock data when dataset not available."""
        loader = KaggleDataLoader()
        jobs = loader.fetch(limit=10)
        
        assert len(jobs) <= 10
        assert all(isinstance(job, JobPosting) for job in jobs)
        assert all(job.source == "kaggle" for job in jobs)


class TestDataPipeline:
    """Test the data pipeline."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = DataPipeline()
        assert pipeline.jobs == []
        assert isinstance(pipeline.linkedin_scraper, LinkedInScraper)
        assert isinstance(pipeline.kaggle_loader, KaggleDataLoader)

    def test_pipeline_run(self):
        """Test running the pipeline."""
        pipeline = DataPipeline()
        jobs = pipeline.run(
            sources=["linkedin", "kaggle"],
            keywords=["Python Developer"],
            limit_per_source=5
        )
        
        assert isinstance(jobs, list)
        assert all(isinstance(job, JobPosting) for job in jobs)
        assert len(pipeline.processing_log) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
