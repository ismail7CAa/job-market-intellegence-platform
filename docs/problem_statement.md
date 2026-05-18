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

### 11. CI Dependencies Drifted from the Application

The GitHub Actions test job installed a short manual dependency list. As the application matured, tests started importing packages that were not in that list, such as `pandera`, `pydantic-settings`, `fastapi`, `loguru`, and `scikit-learn`.

Solved by:

- updating `.github/workflows/ci-cd.yml` with the lightweight dependencies needed by the test/runtime surface
- keeping the full research/orchestration dependencies out of the CI test bootstrap
- rerunning the full local suite before pushing fixes

Outcome:

- test collection works in GitHub Actions
- CI now catches behavior regressions rather than failing on missing imports
- the dependency boundary between test/runtime and future heavy tooling is clearer

Lesson learned:

- a curated CI dependency list is faster than installing everything, but it must be maintained as the application imports evolve

### 12. Pandera Validation Exposed Serialization Differences

CI used a stricter/newer validation path than the earlier local environment. Pydantic JSON serialization converted `posted_date` values into strings, and nullable `url` values stayed as object dtype. Pandera rejected those columns during pipeline tests.

Solved by:

- changing job serialization at dataframe boundaries to preserve Python datetime objects
- making `posted_date` a `pa.DateTime` column with coercion
- allowing nullable URL values to coerce consistently

Outcome:

- the pipeline schema now behaves consistently in CI and local execution
- datetime validation is more explicit
- pipeline boundary contracts are stronger

Lesson learned:

- validation libraries can reveal hidden type assumptions; schema contracts should normalize boundary types intentionally

### 13. The Docker Image Was Too Heavy for GitHub Actions

The first Docker build used the full `requirements.txt`, which includes heavy future-facing tools such as Airflow, dbt, Feast, Torch, Transformers, Prophet, and XGBoost. The GitHub Actions runner ran out of disk space during the build.

Solved by:

- adding `requirements-runtime.txt` for the deployed FastAPI image
- updating `Dockerfile` to install runtime-only dependencies
- tightening `.dockerignore` to exclude `.venv`, MLflow artifacts, notebooks, Terraform, local databases, and nested repository copies

Outcome:

- Docker builds are smaller and more reliable
- the EC2 app image better matches the public serving workload
- heavy tooling remains available in the repository without bloating the runtime container

Lesson learned:

- portfolio systems can include production/future scaffolding, but runtime containers should only ship what they need

### 14. GitHub Actions Deployment Needed Cloud-Network Debugging

The CI/CD deploy job failed in several stages before it could reliably update EC2:

- `ssh-keyscan` failed before useful diagnostics were available
- GitHub Actions could not SSH while the EC2 security group allowed only the developer's IP
- the app directory secret/default expanded incorrectly and created a broken `/database` path
- Docker rejected a GHCR image reference containing uppercase characters from the GitHub owner name

Solved by:

- using `StrictHostKeyChecking=accept-new` on SSH/SCP commands
- documenting that GitHub Actions runners need network access to EC2 port `22`
- replacing the deploy directory expression with `/home/ubuntu/job-market-intelligence-platform`
- using a lowercase GHCR image path

Outcome:

- CI/CD can copy deployment files and restart the app on EC2
- the workflow is easier to debug when secrets or connectivity are wrong
- the deployment path is now reproducible from a push to `main`

Lesson learned:

- a successful SSH login from a laptop does not prove GitHub Actions can reach the server; CI runners are separate network clients

### 15. Runtime Dependencies Were Installed for the Wrong Linux User

The Dockerfile originally installed Python packages with `pip install --user` in the builder stage and copied `/root/.local` into the runtime image. The container then ran as a non-root `appuser`, so Python could not find `uvicorn`.

Solved by:

- installing dependencies into a build prefix
- copying that prefix into `/usr/local`
- keeping the container running as a non-root user

Outcome:

- `python -m uvicorn` works inside the runtime container
- the app can run securely as `appuser`
- dependency visibility no longer depends on root's home directory

Lesson learned:

- non-root containers need dependencies installed in a location visible to the runtime user

### 16. Database Passwords Broke the Connection URL

The deployed app initially reported the database as disconnected. Logs showed the Postgres host was parsed incorrectly because the password was inserted into `DATABASE_URL` and contained URL-special characters.

Solved by:

- changing the GitHub `EC2_DB_PASSWORD` secret to a URL-safe value
- resetting the local Postgres Docker volume so it initialized with the new password

Outcome:

- `/health` reports the database as connected
- the app and Postgres communicate correctly through Docker Compose

Lesson learned:

- secrets placed inside URLs must be URL-safe or URL-encoded; otherwise connection strings can break in non-obvious ways

### 17. The Public URL Needed a Product Surface

After deployment, the root page still looked too much like an API placeholder. For a portfolio project, the first impression should communicate the product and the engineering depth without requiring the reviewer to open Swagger first.

Solved by:

- replacing the simple landing page with a FastAPI-served dashboard
- surfacing market metrics, skills, role forecasts, salary anomalies, city coverage, and work-mode distribution
- adding a visible market-agent query box backed by `/query`
- keeping `/docs` available for technical API inspection

Outcome:

- the live URL now feels like a real product demo
- the AI agent is visible on the frontend
- reviewers can see DE, DS, ML engineering, and AI engineering signals from the first screen

Lesson learned:

- a strong backend project still needs a clear product surface for portfolio review

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
- a deployed FastAPI dashboard at `http://3.121.22.50:8000`
- a working GitHub Actions to GHCR to EC2 deployment flow
- a slim Docker runtime image for the public API/dashboard
- test coverage validating the updated functionality

## Why This Matters

These fixes moved the project from a partially scaffolded system to a working local platform with traceable ML experiments, a more believable API layer, and much stronger alignment between the repository structure and the actual user-facing behavior.

The remaining work is now less about fixing broken wiring and more about product depth, deployment hardening, custom domain/HTTPS setup, agent improvement, and future-scale data sourcing.
