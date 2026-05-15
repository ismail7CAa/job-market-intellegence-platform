# Problem Statement

## Context

The Job Market Intelligence Platform started with strong project breadth across data engineering, analytics, machine learning, API design, and infrastructure scaffolding, but several important parts were still disconnected or incomplete. The main challenge was not a lack of components, but a lack of operational continuity between them.

This document captures the key problems solved so far and the practical outcomes of that work.

## Problems Solved

### 1. Pipeline, API, and CLI Were Out of Sync

The API and CLI expected the data pipeline to expose export and statistics methods, but the `DataPipeline` class did not yet implement them. This created a mismatch between the public interface and the actual pipeline behavior.

Solved by:

- adding pipeline statistics generation
- adding CSV and JSON export support
- introducing consistent job serialization across Pydantic versions

Outcome:

- the pipeline, API, and CLI now share a coherent data flow
- job statistics can be returned and exported reliably

### 2. Experiment Tracking Existed as a Goal, Not a Working Workflow

The project needed versioned model runs, metrics, artifacts, and a model registry, but there was no working end-to-end MLflow training workflow.

Solved by:

- integrating MLflow tracking into the role prediction workflow
- logging dataset fingerprints, parameters, metrics, and artifacts
- registering trained models in the local MLflow model registry
- fixing MLflow artifact path handling so local runs succeed cleanly

Outcome:

- tracked runs now produce `mlflow.db`, artifact outputs, and registered model versions
- the project can compare model improvements through reproducible experiment runs

### 3. Several API Endpoints Were Still Placeholders

Important API routes for role prediction, query answering, and salary anomaly handling returned placeholder responses rather than real outputs.

Solved by:

- implementing salary anomaly detection logic
- implementing a lightweight natural-language query processor
- connecting the prediction endpoint to the trained role prediction model
- adding local CSV fallback data loading for development workflows

Outcome:

- the API now returns usable responses for role predictions, anomalies, and query answers
- the application is much closer to functioning as a demonstrable product locally

### 4. The Initial Role Model Baseline Was Too Weak

The first tracked role prediction baseline worked technically, but its performance was not strong enough to support confidence in the output.

Initial state:

- accuracy around `0.60`
- macro F1 around `0.38`
- several classes were never predicted correctly

Solved by:

- improving the feature set
- adding `location` as an explicit feature
- expanding the text vectorization range
- switching to class-balanced logistic regression

Outcome:

- improved tracked run achieved accuracy `0.90`
- improved tracked run achieved macro F1 approximately `0.93`
- model version `2` was registered in MLflow

### 5. Warning and Maintainability Debt Needed Cleanup

The project had avoidable technical debt from deprecated interfaces and noisy warnings, especially around Pydantic serialization and UTC datetime handling.

Solved by:

- replacing deprecated `.dict()` usage in updated test paths
- moving database models and repository logic toward timezone-aware UTC handling
- updating SQLAlchemy base import usage
- cleaning API imports and reducing avoidable noise

Outcome:

- test output is cleaner
- the codebase is more maintainable and more professional to present

### 6. Documentation Did Not Reflect the Real Project State

The README was still closer to an early draft than a professional summary of the current platform.

Solved by:

- rewriting the README around the real implemented capabilities
- documenting API capabilities, local workflows, MLflow usage, and project structure

Outcome:

- the repository now presents a clearer and more credible project narrative

### 7. Deployment Path Could Accidentally Become Too Expensive

The repository included Terraform, ECS, Kubernetes, RDS, and other production-style infrastructure scaffolding. Those components are useful for showing future direction, but they are not the right default for a portfolio deployment on a newly activated AWS account because they can create ongoing charges.

Solved by:

- making one EC2 instance with Docker Compose the default deployment path
- keeping Postgres as a local container with a persistent Docker volume
- documenting which AWS services to avoid for the first public demo
- wiring GitHub Actions and the manual deploy script around the EC2 path

Outcome:

- the project now has a practical low-cost deployment story
- the production scaffolding remains available without being the default path
- the public demo can be launched without introducing RDS, ECS, ALB, NAT Gateway, or Kubernetes costs

### 8. Database Setup Was Not Fully Aligned with the Application Models

The deployment SQL file was named `init.sql`, but it still contained shell-script lines and had column definitions that did not fully match the SQLAlchemy models. That mismatch could cause confusing behavior when the app starts against Postgres on EC2.

Solved by:

- converting `database/init.sql` into valid PostgreSQL SQL
- aligning table columns with the SQLAlchemy models
- adding the expected indexes and uniqueness constraint
- changing salary defaults from USD to EUR for the German market demo
- adding a real database health check through SQLAlchemy

Outcome:

- the EC2 Postgres container can initialize with the schema expected by the app
- `/health` now checks an actual database query instead of only checking whether initialization happened
- the database layer is more credible as part of the portfolio demo

### 9. The Demo Needed a Clear Market Focus

The sample data and public-facing API text were still mostly generic or US-oriented. For a portfolio project, a focused market story is stronger than a vague global one.

Solved by:

- shifting the project narrative toward the German tech job market
- replacing local sample CSVs with German cities, companies, and EUR salaries
- updating default search keywords toward German roles and locations
- turning the root API route into a small portfolio landing page

Outcome:

- the public demo has a clearer audience and purpose
- salary and location outputs are internally consistent
- recruiters or reviewers can understand the product surface immediately from `/`

### 10. Live Data Collection Was Not Yet Safe Enough for a Public Demo

The project supports real ingestion paths conceptually, but fully live collection has practical and legal constraints: job-board access rules, API credentials, rate limits, dataset licensing, unstable schemas, and data quality drift.

Solved by:

- using a small, committed German demo dataset for the public portfolio version
- keeping API keys and source-specific ingestion configurable for later
- documenting demo data as a deliberate decision rather than pretending it is full production ingestion

Outcome:

- the deployed app is reproducible and reliable for reviewers
- the system can demonstrate analytics, ML, and API behavior without depending on external credentials
- future live-data work remains possible once a compliant data source is chosen

## Current State

At this stage, the platform now has:

- a functioning local data pipeline workflow
- exportable job statistics
- working skill demand analysis
- working salary anomaly detection
- a working MLflow-backed experiment tracking workflow
- a materially improved role prediction baseline
- API endpoints with real behavior for several previously unfinished areas
- a Germany-focused portfolio demo dataset
- a one-EC2 Docker Compose deployment path
- a Postgres schema aligned with the application models
- test coverage validating the updated functionality

## Why This Matters

These fixes moved the project from a partially scaffolded system to a working local platform with traceable ML experiments, a more believable API layer, and much stronger alignment between the repository structure and the actual user-facing behavior.

The remaining work is now less about fixing broken wiring and more about product depth, deployment hardening, and future-scale improvements.
