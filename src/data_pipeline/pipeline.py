"""Data pipeline orchestrator for coordinating data collection and processing."""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Dict, List

from kafka import KafkaProducer

from config.settings import get_settings
from .models import JobPosting
from .providers import (
    JobPostingProvider,
    JobSearchRequest,
    KaggleJobProvider,
    LinkedInJobProvider,
    LocalCsvJobProvider,
    MockCompanyFeedProvider,
)
from .scraper import LinkedInScraper, KaggleDataLoader
from .validation import validate_job_postings

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrates data collection from multiple sources."""

    def __init__(
        self,
        kafka_bootstrap_servers: str = None,
        providers: Dict[str, JobPostingProvider] | None = None,
    ):
        """Initialize the data pipeline."""
        settings = get_settings()
        self.jobs: List[JobPosting] = []
        self.linkedin_scraper = LinkedInScraper()
        self.kaggle_loader = KaggleDataLoader()
        self.providers = providers or {
            "linkedin": LinkedInJobProvider(self.linkedin_scraper),
            "kaggle": KaggleJobProvider(self.kaggle_loader),
            "legal_demo_csv": LocalCsvJobProvider(settings.production_data_path),
            "local_csv": LocalCsvJobProvider(
                settings.production_data_path,
                source_id="local_csv",
                legal_basis="Local legal seed data for development.",
            ),
            "company_feed": MockCompanyFeedProvider(),
        }
        self.processing_log = []
        self.kafka_bootstrap_servers = (
            kafka_bootstrap_servers
            if kafka_bootstrap_servers is not None
            else settings.kafka_bootstrap_servers
        )
        self.kafka_topic = settings.kafka_topic
        self._producer = None

    @property
    def producer(self):
        """Lazy initialization of Kafka producer."""
        if self._producer is None and self.kafka_bootstrap_servers:
            self._producer = KafkaProducer(
                bootstrap_servers=[self.kafka_bootstrap_servers],
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
        return self._producer

    @staticmethod
    def _job_to_dict(job: JobPosting | Dict) -> Dict:
        """Serialize a job posting consistently across Pydantic versions."""
        if isinstance(job, dict):
            return job
        if hasattr(job, "model_dump"):
            return job.model_dump(mode="json")
        return job.dict()

    def run(
        self,
        sources: List[str] = None,
        keywords: List[str] = None,
        limit_per_source: int = 100
    ) -> dict:
        """Run the complete data pipeline.
        
        Args:
            sources: List of data sources ("linkedin", "kaggle")
            keywords: Job search keywords
            limit_per_source: Max jobs per source
            
        Returns:
            Dict with processing statistics
        """
        if sources is None:
            sources = get_settings().default_sources
        if keywords is None:
            keywords = get_settings().default_keywords

        logger.info(f"Starting data pipeline with sources: {sources}")
        start_time = datetime.now()

        try:
            request = JobSearchRequest(keywords=keywords, limit=limit_per_source)
            for source in sources:
                self._fetch_from_provider(source, request)

            validate_job_postings(self.jobs)

            # Send jobs to Kafka
            self._send_to_kafka()

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Pipeline completed in {elapsed:.2f}s with {len(self.jobs)} jobs sent to Kafka")
            return self.jobs

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            raise

    def register_provider(self, provider: JobPostingProvider) -> None:
        """Register or replace a provider adapter by source id."""
        self.providers[provider.source_id] = provider

    def get_statistics(self) -> Dict:
        """Return summary statistics for the currently loaded jobs."""
        if not self.jobs:
            return {
                "total_jobs": 0,
                "locations": 0,
                "companies": 0,
                "unique_skills": 0,
                "salary_stats": {},
                "top_skills": [],
                "sources": {},
            }

        job_dicts = [self._job_to_dict(job) for job in self.jobs]
        locations = Counter(job["location"] for job in job_dicts if job.get("location"))
        companies = Counter(job["company"] for job in job_dicts if job.get("company"))
        skills = Counter(
            skill
            for job in job_dicts
            for skill in job.get("required_skills", [])
        )
        sources = Counter(job["source"] for job in job_dicts if job.get("source"))

        salary_values = [
            (job["salary_min"] + job["salary_max"]) / 2
            for job in job_dicts
            if job.get("salary_min") is not None and job.get("salary_max") is not None
        ]

        salary_stats = {}
        if salary_values:
            salary_stats = {
                "count": len(salary_values),
                "mean": mean(salary_values),
                "median": median(salary_values),
                "min": min(salary_values),
                "max": max(salary_values),
            }

        return {
            "total_jobs": len(job_dicts),
            "locations": len(locations),
            "companies": len(companies),
            "unique_skills": len(skills),
            "salary_stats": salary_stats,
            "top_skills": skills.most_common(10),
            "sources": dict(sources),
        }

    def save_to_csv(self, output_path: str) -> None:
        """Persist the current jobs to CSV."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        job_dicts = [self._job_to_dict(job) for job in self.jobs]
        frame = validate_job_postings(job_dicts)
        if "required_skills" in frame.columns:
            frame["required_skills"] = frame["required_skills"].apply(
                lambda skills: ";".join(skills) if isinstance(skills, list) else skills
            )
        frame.to_csv(output, index=False)

    def save_to_json(self, output_path: str) -> None:
        """Persist the current jobs to JSON."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        job_dicts = [self._job_to_dict(job) for job in self.jobs]
        validate_job_postings(job_dicts)
        output.write_text(
            json.dumps(job_dicts, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _fetch_from_provider(self, source: str, request: JobSearchRequest) -> None:
        """Fetch jobs from a registered provider."""
        source_key = source.lower()
        provider = self.providers.get(source_key)
        if provider is None:
            raise ValueError(f"No provider registered for source '{source}'.")

        logger.info(f"Fetching from provider {source_key}")
        try:
            jobs = provider.fetch(request)
            self.jobs.extend(jobs)
            self.processing_log.append({
                "source": source_key,
                "job_count": len(jobs),
                "legal_basis": getattr(provider, "legal_basis", None),
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.error(f"{source_key} provider fetch error: {str(e)}")
            self.processing_log.append({
                "source": source_key,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
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

    def _send_to_kafka(self) -> None:
        """Send collected jobs to Kafka topic."""
        if not self.producer:
            logger.warning("Kafka producer not configured, skipping send to Kafka")
            return

        validate_job_postings(self.jobs)

        logger.info(f"Sending {len(self.jobs)} jobs to Kafka")
        for job in self.jobs:
            try:
                future = self.producer.send(self.kafka_topic, self._job_to_dict(job))
                future.get(timeout=10)  # Wait for send to complete
            except Exception as e:
                logger.error(f"Failed to send job {job.id} to Kafka: {str(e)}")
        self.producer.flush()
