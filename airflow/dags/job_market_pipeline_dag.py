from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import sys
import os

# Add src to path
sys.path.append('/app/src')

from data_pipeline.pipeline import DataPipeline

default_args = {
    'owner': 'job_market',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'job_market_pipeline',
    default_args=default_args,
    description='Job Market Intelligence Data Pipeline',
    schedule_interval=timedelta(hours=6),  # Run every 6 hours
    catchup=False,
    max_active_runs=1,
)

def run_data_pipeline(**kwargs):
    """Run the data pipeline."""
    pipeline = DataPipeline(kafka_bootstrap_servers='kafka:9092')
    result = pipeline.run()
    print(f"Pipeline completed: {result}")
    return result

run_pipeline_task = PythonOperator(
    task_id='run_data_pipeline',
    python_callable=run_data_pipeline,
    dag=dag,
)