"""Data pipeline orchestrator for coordinating data collection and processing."""

import logging
from typing import List, Optional
from datetime import datetime
import json
from kafka import KafkaProducer
from .models import JobPosting
from .scraper import LinkedInScraper, KaggleDataLoader

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrates data collection from multiple sources."""

    def __init__(self, kafka_bootstrap_servers: str = None):
        """Initialize the data pipeline."""
        self.jobs: List[JobPosting] = []
        self.linkedin_scraper = LinkedInScraper()
        self.kaggle_loader = KaggleDataLoader()
        self.processing_log = []
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
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
            sources = ["linkedin", "kaggle"]
        if keywords is None:
            keywords = ["Python Developer", "Data Scientist", "DevOps Engineer"]

        logger.info(f"Starting data pipeline with sources: {sources}")
        start_time = datetime.now()

        try:
            # Fetch from each source and send to Kafka
            for source in sources:
                if source.lower() == "linkedin":
                    self._fetch_from_linkedin(keywords, limit_per_source)
                elif source.lower() == "kaggle":
                    self._fetch_from_kaggle(limit_per_source)

            # Send jobs to Kafka
            self._send_to_kafka()

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Pipeline completed in {elapsed:.2f}s with {len(self.jobs)} jobs sent to Kafka")
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

    def _send_to_kafka(self) -> None:
        """Send collected jobs to Kafka topic."""
        if not self.producer:
            logger.warning("Kafka producer not configured, skipping send to Kafka")
            return
        
        logger.info(f"Sending {len(self.jobs)} jobs to Kafka")
        for job in self.jobs:
            try:
                future = self.producer.send('job_postings', job.dict())
                future.get(timeout=10)  # Wait for send to complete
            except Exception as e:
                logger.error(f"Failed to send job {job.id} to Kafka: {str(e)}")
        self.producer.flush()
