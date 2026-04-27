"""Data collection module for job postings from various sources."""

from typing import List, Dict, Optional
import logging
import requests
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from config.settings import get_settings
from .models import JobPosting

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def fetch(self, **kwargs) -> List[JobPosting]:
        """Fetch job postings from the data source."""
        pass


class LinkedInScraper(DataSource):
    """Scrape job postings from LinkedIn via API."""

    def __init__(self, api_key: str = None):
        """Initialize LinkedIn scraper with API key.
        
        Args:
            api_key: LinkedIn API key for authentication
        """
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.linkedin_api_key
        self.base_url = "https://api.linkedin.com/v2"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            })

    def fetch(
        self, 
        keyword: str, 
        location: str = "",
        limit: int = 100,
        job_type: str = ""
    ) -> List[JobPosting]:
        """Fetch job postings matching criteria.
        
        Args:
            keyword: Job title or keyword to search
            location: Job location filter
            limit: Maximum number of results
            job_type: Filter by job type (e.g., "Full-time")
            
        Returns:
            List of JobPosting objects
        """
        logger.info(f"Fetching {limit} jobs for '{keyword}' from LinkedIn")
        
        if not self.api_key:
            logger.warning("LinkedIn API key not set, returning mock data")
            return self._get_mock_data(keyword, limit)
        
        try:
            # Build query parameters
            params = {
                "keywords": keyword,
                "count": min(limit, 100),  # LinkedIn API limit
            }
            if location:
                params["locations"] = location
            
            # Fetch from LinkedIn API
            response = self.session.get(
                f"{self.base_url}/jobs/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            jobs = []
            for job_data in response.json().get("elements", []):
                job = self._parse_linkedin_job(job_data)
                if job:
                    jobs.append(job)
            
            logger.info(f"Successfully fetched {len(jobs)} jobs from LinkedIn")
            return jobs
            
        except Exception as e:
            logger.error(f"Error fetching from LinkedIn: {str(e)}")
            return self._get_mock_data(keyword, limit)

    def _parse_linkedin_job(self, job_data: Dict) -> Optional[JobPosting]:
        """Parse LinkedIn job data into JobPosting model."""
        try:
            return JobPosting(
                id=job_data.get("id", ""),
                title=job_data.get("title", ""),
                company=job_data.get("company", {}).get("name", ""),
                location=job_data.get("location", ""),
                salary_min=job_data.get("salary", {}).get("minimum"),
                salary_max=job_data.get("salary", {}).get("maximum"),
                job_type=job_data.get("jobType", "Full-time"),
                description=job_data.get("description", ""),
                required_skills=self._extract_skills(job_data.get("description", "")),
                posted_date=datetime.fromisoformat(job_data.get("postedDate", "")),
                source="linkedin",
                url=job_data.get("url")
            )
        except Exception as e:
            logger.warning(f"Failed to parse LinkedIn job: {str(e)}")
            return None

    def _extract_skills(self, text: str) -> List[str]:
        """Extract required skills from job description text."""
        # Simple skill extraction - can be enhanced with NLP
        common_skills = [
            "Python", "Java", "JavaScript", "SQL", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "React", "Vue", "Angular", "Node.js",
            "Django", "FastAPI", "Spring", "Go", "Rust", "TypeScript",
            "Machine Learning", "Data Science", "Analytics", "DevOps"
        ]
        found_skills = [skill for skill in common_skills if skill.lower() in text.lower()]
        return found_skills

    def _get_mock_data(self, keyword: str, limit: int) -> List[JobPosting]:
        """Return mock data for testing."""
        mock_jobs = [
            JobPosting(
                id=f"linkedin_{i}",
                title=f"{keyword} - Level {i}",
                company=f"Tech Company {i}",
                location="San Francisco, CA",
                salary_min=100000 + (i * 10000),
                salary_max=150000 + (i * 20000),
                job_type="Full-time",
                description=f"This is a mock {keyword} position",
                required_skills=["Python", "FastAPI", "Docker"],
                posted_date=datetime.now(),
                source="linkedin"
            )
            for i in range(min(limit, 5))
        ]
        return mock_jobs


class KaggleDataLoader(DataSource):
    """Load job market data from Kaggle datasets."""

    def __init__(self, dataset_id: str = None, api_key: str = None, raw_data_dir: str | Path = None):
        """Initialize Kaggle data loader.
        
        Args:
            dataset_id: Kaggle dataset ID or slug
            api_key: Kaggle API key
        """
        settings = get_settings()
        self.dataset_id = dataset_id if dataset_id is not None else settings.kaggle_dataset_id
        self.api_key = api_key if api_key is not None else settings.kaggle_api_key
        self.raw_data_dir = Path(raw_data_dir) if raw_data_dir is not None else settings.kaggle_raw_data_dir

    def fetch(self, limit: int = 1000) -> List[JobPosting]:
        """Load and parse Kaggle dataset.
        
        Args:
            limit: Maximum number of records to load
            
        Returns:
            List of JobPosting objects
        """
        logger.info(f"Loading dataset from Kaggle")
        
        if not self.dataset_id:
            logger.warning("Kaggle dataset ID not set, returning mock data")
            return self._get_mock_data(limit)
        
        try:
            # Try to load from Kaggle API
            from kaggle.api.kaggle_api_extended import KaggleApi
            api = KaggleApi()
            api.authenticate()
            
            # Download dataset
            api.dataset_download_files(self.dataset_id, path=str(self.raw_data_dir), unzip=True)
            
            # Load and parse CSV files
            jobs = self._load_csv_files(limit)
            logger.info(f"Successfully loaded {len(jobs)} jobs from Kaggle")
            return jobs
            
        except Exception as e:
            logger.error(f"Error loading from Kaggle: {str(e)}")
            logger.info("Falling back to mock data")
            return self._get_mock_data(limit)

    def _load_csv_files(self, limit: int) -> List[JobPosting]:
        """Load and parse CSV files from Kaggle dataset."""
        import glob
        jobs = []
        
        csv_files = glob.glob(str(self.raw_data_dir / "*.csv"))
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                for _, row in df.head(limit - len(jobs)).iterrows():
                    job = self._parse_kaggle_job(row)
                    if job:
                        jobs.append(job)
                if len(jobs) >= limit:
                    break
            except Exception as e:
                logger.warning(f"Error loading {csv_file}: {str(e)}")
        
        return jobs

    def _parse_kaggle_job(self, row) -> Optional[JobPosting]:
        """Parse Kaggle CSV row into JobPosting model."""
        try:
            # Adjust column names based on actual Kaggle dataset
            return JobPosting(
                id=str(row.get("id", row.name)),
                title=row.get("job_title", row.get("title", "")),
                company=row.get("company_name", row.get("company", "")),
                location=row.get("location", ""),
                salary_min=self._parse_salary_value(row.get("min_salary")),
                salary_max=self._parse_salary_value(row.get("max_salary")),
                job_type=row.get("job_type", "Full-time"),
                description=row.get("job_description", row.get("description", "")),
                required_skills=self._extract_skills_from_description(
                    str(row.get("job_description", "") or "")
                ),
                posted_date=datetime.now(),
                source="kaggle"
            )
        except Exception as e:
            logger.warning(f"Failed to parse Kaggle job: {str(e)}")
            return None

    @staticmethod
    def _parse_salary_value(value) -> Optional[float]:
        """Return a positive salary value or None when the source is missing it."""
        if pd.isna(value):
            return None
        salary = float(value)
        return salary if salary > 0 else None

    def _extract_skills_from_description(self, text: str) -> List[str]:
        """Extract required skills from job description text."""
        common_skills = [
            "Python", "Java", "JavaScript", "SQL", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "React", "Vue", "Angular", "Node.js",
            "Django", "FastAPI", "Spring", "Go", "Rust", "TypeScript",
            "Machine Learning", "Data Science", "Analytics", "DevOps"
        ]
        found_skills = [skill for skill in common_skills if skill.lower() in text.lower()]
        return list(set(found_skills))  # Remove duplicates

    def _get_mock_data(self, limit: int) -> List[JobPosting]:
        """Return mock Kaggle data for testing."""
        mock_jobs = [
            JobPosting(
                id=f"kaggle_{i}",
                title=f"Data {['Scientist', 'Engineer', 'Analyst'][i % 3]}",
                company=f"Data Company {i}",
                location=["New York, NY", "San Francisco, CA", "Austin, TX"][i % 3],
                salary_min=90000 + (i * 5000),
                salary_max=140000 + (i * 10000),
                job_type="Full-time",
                description="This is a mock job posting from Kaggle dataset",
                required_skills=["Python", "SQL", "Machine Learning"],
                posted_date=datetime.now(),
                source="kaggle"
            )
            for i in range(min(limit, 10))
        ]
        return mock_jobs
