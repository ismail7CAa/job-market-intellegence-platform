# Job Market Intelligence Platform

A job market analytics platform for collecting job postings, analyzing skill demand and salary patterns, tracking machine learning experiments, and exposing insights through a REST API.

## What It Does

- Tracks skill demand shifts across job postings
- Detects salary anomalies and outliers
- Forecasts in-demand role categories
- Answers lightweight natural-language job market questions
- Tracks model runs, metrics, artifacts, and model versions with MLflow

## Current Capabilities

### Data Engineering

- Multi-source ingestion through the `DataPipeline`
- Export to CSV and JSON
- Job-level summary statistics for locations, companies, skills, and salary ranges
- Local sample datasets in `data/` for development and testing

### Data Science

- Skill demand analysis and salary premium reporting
- Salary anomaly detection
- Role classification and simple demand forecasting
- MLflow experiment tracking with a local registry

### API

The FastAPI app currently supports:

- `/health`
- `/data/fetch`
- `/analyze/skills`
- `/trends/skills`
- `/skills/{skill_name}/salary-premium`
- `/skills/{skill_name}/related`
- `/predict/roles`
- `/query`
- `/salary/anomalies`
- `/report/skill-demand`
- `/export/skills-csv`
- `/status/pipeline`
- `/stats/jobs`

When live-ingested jobs are not loaded yet, the API can fall back to the local sample CSV datasets for development workflows.

## Project Structure

- `src/data_pipeline/`: ingestion, scraping, export, and pipeline stats
- `src/analytics/`: skill demand and salary analysis
- `src/prediction/`: role prediction and MLflow-backed training workflow
- `src/api/`: FastAPI application
- `src/nlp/`: lightweight natural-language query handling
- `tests/`: pipeline, analytics, database, API, and experiment-tracking tests
- `terraform/`, `k8s/`, `scripts/`: infrastructure and deployment scaffolding

## Local Development

Install dependencies in your virtual environment, then run the API locally:

```bash
uvicorn src.api.main:app --reload
```

Run the test suite:

```bash
pytest
```

## Experiment Tracking

The project includes MLflow-based experiment tracking for role prediction runs using the datasets in `data/`.

Run a tracked experiment locally:

```bash
python cli.py track-experiment \
  --train-data data/job_postings_training.csv \
  --eval-data data/job_postings_production.csv
```

This workflow logs:

- Versioned runs with dataset fingerprints
- Evaluation metrics such as accuracy and macro F1
- Artifacts including predictions, a classification report, and a confusion matrix
- Registered model versions in the MLflow model registry

Default local MLflow configuration:

- Tracking URI: `sqlite:///mlflow.db`
- Artifact root: `./mlartifacts`
- Experiment name: `job-market-role-prediction`
- Registered model name: `job_market_role_predictor`

Open the MLflow UI locally:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

For more detail, see [MLFLOW_SETUP.md](MLFLOW_SETUP.md).

## Infrastructure

AWS, Docker, Kubernetes, and Terraform scaffolding are included, but cloud deployment is intentionally staged for later. For infrastructure notes, see [INFRASTRUCTURE.md](INFRASTRUCTURE.md).

## Status

The repository is in active development. Core local workflows for pipeline analysis, API usage, testing, and MLflow-backed experimentation are in place.
