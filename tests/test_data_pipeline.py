"""Tests for the data pipeline."""

import json
from datetime import datetime, timedelta

import pandas as pd
import pandera.errors as pa_errors
import pytest

from src.data_pipeline.models import JobPosting
from src.data_pipeline.scraper import LinkedInScraper, KaggleDataLoader
from src.data_pipeline.pipeline import DataPipeline
from src.data_pipeline.validation import validate_job_postings


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
        assert job.currency == "EUR"
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

    def test_parse_kaggle_job_treats_zero_salary_as_missing(self):
        """Test sparse Kaggle rows do not create fake zero salaries."""
        loader = KaggleDataLoader()
        row = pd.Series(
            {
                "id": "row_1",
                "job_title": "Data Analyst",
                "company_name": "Data Co",
                "location": "Remote",
                "min_salary": 0,
                "max_salary": 0,
                "job_type": "Full-time",
                "job_description": "SQL and Python analytics",
            }
        )

        job = loader._parse_kaggle_job(row)

        assert job.salary_min is None
        assert job.salary_max is None


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

    def test_pipeline_output_matches_schema_contract(self):
        """Test successful pipeline output satisfies the dataframe schema."""
        pipeline = DataPipeline()
        pipeline.run(
            sources=["linkedin", "kaggle"],
            keywords=["Python Developer"],
            limit_per_source=2
        )

        validated = validate_job_postings(pipeline.jobs)

        assert len(validated) == len(pipeline.jobs)
        assert validated["id"].notna().all()
        assert validated["posted_date"].notna().all()

    def test_get_statistics(self):
        """Test pipeline statistics generation."""
        pipeline = DataPipeline()
        pipeline.run(
            sources=["linkedin", "kaggle"],
            keywords=["Python Developer"],
            limit_per_source=3
        )

        stats = pipeline.get_statistics()

        assert stats["total_jobs"] == len(pipeline.jobs)
        assert stats["locations"] > 0
        assert stats["companies"] > 0
        assert stats["unique_skills"] > 0
        assert "top_skills" in stats
        assert "sources" in stats

    def test_save_to_csv_and_json(self, tmp_path):
        """Test exporting pipeline data to CSV and JSON."""
        pipeline = DataPipeline()
        pipeline.run(
            sources=["linkedin", "kaggle"],
            keywords=["Python Developer"],
            limit_per_source=2
        )

        csv_path = tmp_path / "jobs.csv"
        json_path = tmp_path / "jobs.json"

        pipeline.save_to_csv(str(csv_path))
        pipeline.save_to_json(str(json_path))

        assert csv_path.exists()
        assert json_path.exists()
        assert "required_skills" in csv_path.read_text(encoding="utf-8")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(payload) == len(pipeline.jobs)
        assert all("title" in item for item in payload)

    def test_validation_rejects_negative_salary(self):
        """Test dataframe contract rejects impossible salary values."""
        invalid_job = JobPosting(
            id="job_bad_salary",
            title="Data Engineer",
            company="Example Corp",
            location="Remote",
            salary_min=-1,
            salary_max=120000,
            job_type="Full-time",
            description="Build data pipelines",
            required_skills=["Python", "SQL"],
            posted_date=datetime.now(),
            source="linkedin",
        )

        with pytest.raises(pa_errors.SchemaErrors):
            validate_job_postings([invalid_job])

    def test_validation_rejects_future_posted_date(self):
        """Test dataframe contract rejects timestamps beyond current time."""
        future_job = JobPosting(
            id="job_future",
            title="Analytics Engineer",
            company="Example Corp",
            location="Remote",
            salary_min=100000,
            salary_max=130000,
            job_type="Full-time",
            description="Own analytics models",
            required_skills=["Python", "SQL"],
            posted_date=datetime.now() + timedelta(days=1),
            source="kaggle",
        )

        with pytest.raises(pa_errors.SchemaErrors):
            validate_job_postings([future_job])

    def test_validation_rejects_null_required_column(self):
        """Test dataframe contract requires core fields before export."""
        invalid_job = {
            "id": "job_missing_company",
            "title": "Python Developer",
            "company": None,
            "location": "Austin, TX",
            "salary_min": 100000,
            "salary_max": 140000,
            "currency": "USD",
            "job_type": "Full-time",
            "description": "Build APIs",
            "required_skills": ["Python"],
            "posted_date": datetime.now(),
            "source": "linkedin",
        }

        with pytest.raises(pa_errors.SchemaErrors):
            validate_job_postings([invalid_job])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
