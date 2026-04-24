# Job Market Intelligence Platform

The project is under deployment.

## Overview

A comprehensive system that analyzes job market trends using real-world data sources. This platform:

- **Tracks Skill Demand Shifts**: Monitors changes in skill demand across the job market over time
- **Detects Salary Anomalies**: Identifies unusual salary patterns and outliers
- **Predicts Role Spikes**: Machine learning models predict which roles will be in high demand next quarter
- **Natural Language Interface**: Ask the system questions about the job market in plain English

## Architecture

- **Data Pipeline**: Ingests data from LinkedIn API/scraping or Kaggle datasets
- **Analytics Engine**: Processes and analyzes job posting data
- **Prediction Models**: Forecasts future job market trends
- **NLP Module**: Converts natural language questions into data queries
- **REST API**: Exposes functionality through HTTP endpoints

## Data Sources

- LinkedIn job postings (via API or scraping)
- Kaggle job market datasets

## Status

Under active development# job-market-intellegence-platform

## Experiment Tracking

The project now includes MLflow-based experiment tracking for role prediction runs using the training and production datasets in `data/`.

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
- A registered model in the MLflow model registry

Default local MLflow configuration:

- Tracking URI: `sqlite:///mlflow.db`
- Artifact root: `./mlartifacts`
- Experiment name: `job-market-role-prediction`
- Registered model name: `job_market_role_predictor`

To inspect the runs in the UI:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
