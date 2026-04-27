"""Kafka consumer to process job postings and load to BigQuery."""

import logging
import json
from kafka import KafkaConsumer
from google.cloud import bigquery
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger(__name__)

class JobPostingConsumer:
    """Consumes job postings from Kafka and loads to BigQuery."""

    def __init__(self, kafka_bootstrap_servers: str = None,
                 bigquery_project: str = None,
                 bigquery_dataset: str = None):
        settings = get_settings()
        kafka_bootstrap_servers = kafka_bootstrap_servers or settings.kafka_bootstrap_servers
        bigquery_project = bigquery_project or settings.bigquery_project
        bigquery_dataset = bigquery_dataset or settings.bigquery_dataset
        if not kafka_bootstrap_servers:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS must be configured to run the consumer.")
        if not bigquery_project:
            raise ValueError("BIGQUERY_PROJECT must be configured to run the consumer.")

        self.consumer = KafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=[kafka_bootstrap_servers],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=settings.kafka_consumer_group_id
        )
        self.bq_client = bigquery.Client(project=bigquery_project)
        self.dataset_id = bigquery_dataset
        self.table_id = f"{bigquery_project}.{bigquery_dataset}.{settings.bigquery_table}"

    def create_table_if_not_exists(self):
        """Create BigQuery table if it doesn't exist."""
        schema = [
            bigquery.SchemaField("id", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("company", "STRING"),
            bigquery.SchemaField("location", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("salary_min", "FLOAT"),
            bigquery.SchemaField("salary_max", "FLOAT"),
            bigquery.SchemaField("required_skills", "STRING", mode="REPEATED"),
            bigquery.SchemaField("posted_date", "DATE"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
        ]

        table = bigquery.Table(self.table_id, schema=schema)
        try:
            self.bq_client.create_table(table)
            logger.info(f"Created table {self.table_id}")
        except Exception as e:
            if "Already Exists" in str(e):
                logger.info(f"Table {self.table_id} already exists")
            else:
                raise

    def consume_and_load(self):
        """Consume messages and load to BigQuery."""
        self.create_table_if_not_exists()

        logger.info("Starting Kafka consumer...")
        for message in self.consumer:
            try:
                job_data = message.value
                # Add ingested timestamp
                job_data['ingested_at'] = datetime.now().isoformat()

                # Convert posted_date to date format if needed
                if job_data.get('posted_date'):
                    job_data['posted_date'] = job_data['posted_date'][:10]  # YYYY-MM-DD

                # Insert to BigQuery
                errors = self.bq_client.insert_rows_json(self.table_id, [job_data])
                if errors:
                    logger.error(f"BigQuery insert errors: {errors}")
                else:
                    logger.info(f"Inserted job {job_data.get('id')} to BigQuery")

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")

if __name__ == "__main__":
    consumer = JobPostingConsumer()
    consumer.consume_and_load()
