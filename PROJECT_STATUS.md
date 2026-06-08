# Project Status

## Current Status

The local Docker demo is ready.

The project currently runs as a Docker Compose stack with:

- FastAPI application container
- PostgreSQL container
- FastAPI-served static frontend at `/job-intelligence/`
- job search, filters, job detail, salary context, source governance, and apply handoff
- Docker smoke check through `make docker-check`

Verified local demo path:

```bash
docker compose up --build app
make docker-check
```

Open the product walkthrough at:

```text
http://localhost:8000/job-intelligence/
```

## Deployment Status

The public cloud deployment is not currently live.

The repository includes a one-EC2 Docker Compose deployment path, GHCR-oriented deployment scaffolding, and optional Terraform/Kubernetes infrastructure. Those pieces are documented, but the current portfolio-ready state is the local Docker demo.

## Data Status

The app uses legal synthetic German seed listings for the current portfolio demo.

This is intentional:

- the demo is reproducible
- no unapproved job-board scraping is required
- search, salary context, filters, and apply handoff can be shown consistently
- source governance can clearly separate approved demo data from future live providers

The project does not claim live job-board coverage in its current state.

## Ready To Show

The project is ready to show as a portfolio-grade product slice:

- Dockerized FastAPI + Postgres runtime
- German job-search frontend
- backend search engine with pagination, sorting, filters, relevance scores, and match reasons
- salary context with listed vs estimated salary labels
- source-governance endpoints and blocked unapproved ingestion
- README screenshots and Chrome walkthrough
- operational health and Docker smoke checks

## Future Work

The most important next improvements are:

- connect a live approved job-listing provider under a clear license
- add company career feeds where explicit permission or public feed terms allow storing and linking listings
- add official market-context adapters for Eurostat, Bundesagentur fuer Arbeit, EURES, and ESCO enrichment
- deploy the one-EC2 Docker Compose path publicly with HTTPS and a custom domain
- add scheduled ingestion using the existing `IngestionService`
- add scheduled expiry handling for live provider listings
- add provider-license documentation for any live source
- add a React/Vite frontend if the UI grows beyond the current static search and results workflow
- promote Kafka, dbt, BigQuery, Feast, and Airflow from scaffolded infrastructure to exercised production workflows
- add Docker integration checks to CI against ephemeral services
- add monitoring for data drift, salary distributions, search quality, and model performance

## Not In Scope Yet

These are intentionally not claimed as complete:

- live scraping from LinkedIn, StepStone, Indeed, Glassdoor, or similar job boards
- production live listing coverage
- always-on public deployment
- managed production infrastructure such as RDS, ALB, ECS/Fargate, or Kubernetes
- fully scheduled orchestration across Kafka, dbt, Feast, and BigQuery

The project is complete as a local, reproducible portfolio demo and ready for the next stage of approved live data integration.
