"""Data pipeline orchestrator for coordinating data collection and processing."""

import logging
from typing import List, Optional
from datetime import datetime
import json
from .models import JobPosting
from .scraper import LinkedInScraper, KaggleDataLoader

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrates data collection from multiple sources."""

    def __init__(self):
        """Initialize the data pipeline."""
        self.jobs: List[JobPosting] = []
        self.linkedin_scraper = LinkedInScraper()
        self.kaggle_loader = KaggleDataLoader()
        self.processing_log = []

    def run(
        self,
        sources: List[str] = None,
        keywords: List[str] = None,
        limit_per_source: int = 100
    ) -> List[JobPosting]:
        """Run the complete data pipeline.
        
        Args:
            sources: List of data sources ("linkedin", "kaggle")
            keywords: Job search keywords
            limit_per_source: Max jobs per source
            
        Returns:
            List of processed JobPosting objects
        """
        if sources is None:
            sources = ["linkedin", "kaggle"]
        if keywords is None:
            keywords = ["Python Developer", "Data Scientist", "DevOps Engineer"]

        logger.info(f"Starting data pipeline with sources: {sources}")
        start_time = datetime.now()

        try:
            # Fetch from each source
            for source in sources:
                if source.lower() == "linkedin":
                    self._fetch_from_linkedin(keywords, limit_per_source)
                elif source.lower() == "kaggle":
                    self._fetch_from_kaggle(limit_per_source)

            # Data quality checks
            self._validate_data()

            # Deduplication
            self._deduplicate()

            # Enrichment
            self._enrich_data()

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Pipeline completed in {elapsed:.2f}s with {len(self.jobs)} jobs")
            return self.jobs

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            raise

    def _fetch_from_linkedin(self, keywords: List[str], limit: int) -> None:
        """Fetch jobs from LinkedIn."""
        logger.info(f"Fetching from LinkedIn with keywords: {keywords}")
        try:
            for keyword in keywords:
                jobs = self.linkedin_scraper.fetch(keyword=keyword, limit=limit)
                self.jobs.extend(jobs)
                self.processing_log.append({
                    "source": "linkedin",
                    "keyword": keyword,
                    "job_count": len(jobs),
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"LinkedIn fetch error: {str(e)}")
            self.processing_log.append({
                "source": "linkedin",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def _fetch_from_kaggle(self, limit: int) -> None:
        """Fetch jobs from Kaggle."""
        logger.info("Fetching from Kaggle")
        try:
            jobs = self.kaggle_loader.fetch(limit=limit)
            self.jobs.extend(jobs)
            self.processing_log.append({
                "source": "kaggle",
                "job_count": len(jobs),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Kaggle fetch error: {str(e)}")
            self.processing_log.append({
                "source": "kaggle",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def _validate_data(self) -> None:
        """Validate data quality and remove invalid records."""
        logger.info("Validating data quality")
        initial_count = len(self.jobs)
        
        # Remove jobs with missing critical fields
        self.jobs = [
            job for job in self.jobs
            if job.title and job.company and job.location
        ]
        
        removed = initial_count - len(self.jobs)
        if removed > 0:
            logger.warning(f"Removed {removed} invalid records")

    def _deduplicate(self) -> None:
        """Remove duplicate jobs."""
        logger.info("Deduplicating jobs")
        initial_count = len(self.jobs)
        
        seen_ids = set()
        unique_jobs = []
        
        for job in self.jobs:
            job_key = (job.title.lower(), job.company.lower(), job.location.lower())
            if job_key not in seen_ids:
                seen_ids.add(job_key)
                unique_jobs.append(job)
        
        removed = initial_count - len(unique_jobs)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate jobs")
        self.jobs = unique_jobs

    def _enrich_data(self) -> None:
        """Enrich job data with additional insights."""
        logger.info("Enriching job data")
        
        # Group by skill to calculate skill frequency
        skill_counts = {}
        for job in self.jobs:
            for skill in job.required_skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # Add skill frequency to jobs
        for job in self.jobs:
            # Calculate average salary if available
            if job.salary_min and job.salary_max:
                job_dict = job.dict()
                job_dict["average_salary"] = (job.salary_min + job.salary_max) / 2
                job = JobPosting(**job_dict)

    def save_to_csv(self, filepath: str) -> None:
        """Save jobs to CSV file."""
        try:
            import pandas as pd
            data = [job.dict() for job in self.jobs]
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            logger.info(f"Saved {len(self.jobs)} jobs to {filepath}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {str(e)}")

    def save_to_json(self, filepath: str) -> None:
        """Save jobs to JSON file."""
        try:
            with open(filepath, 'w') as f:
                data = [job.dict(default=str) for job in self.jobs]
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.jobs)} jobs to {filepath}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")

    def get_statistics(self) -> dict:
        """Get pipeline statistics."""
        if not self.jobs:
            return {}

        import statistics

        salaries = [
            (job.salary_min + job.salary_max) / 2
            for job in self.jobs
            if job.salary_min and job.salary_max
        ]

        skill_counts = {}
        for job in self.jobs:
            for skill in job.required_skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1

        return {
            "total_jobs": len(self.jobs),
            "locations": len(set(job.location for job in self.jobs)),
            "companies": len(set(job.company for job in self.jobs)),
            "unique_skills": len(skill_counts),
            "salary_stats": {
                "count": len(salaries),
                "mean": statistics.mean(salaries) if salaries else 0,
                "median": statistics.median(salaries) if salaries else 0,
                "std_dev": statistics.stdev(salaries) if len(salaries) > 1 else 0,
            },
            "top_skills": sorted(
                skill_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "processing_log": self.processing_log
        }
