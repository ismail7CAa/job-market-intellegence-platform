# ADR 003: Why a Local Postgres Container Instead of RDS for the Demo

- Status: Accepted
- Date: 2026-05-16

## Context

The application uses SQLAlchemy models and needs a relational database for deployment. AWS RDS would be a natural production option, but the immediate goal is a low-cost portfolio deployment on one EC2 instance.

For the first public demo, the database needs to:

- initialize consistently
- match the application models
- survive container restarts
- avoid extra managed-service cost
- stay easy to reset during development

## Decision

Use a Postgres container in `docker-compose.free-tier.yml` with a persistent Docker volume.

The container initializes from `database/init.sql`, and the FastAPI app connects through:

```text
postgresql://jobmarket:<password>@postgres:5432/job_market
```

## Options Considered

### Option 1: Postgres Container on EC2

Pros:

- no separate RDS cost
- simple Docker Compose setup
- local and cloud environments are easier to reason about
- database schema can be initialized from the repository
- enough for the small portfolio dataset

Cons:

- backups are not managed automatically
- database availability depends on the EC2 host
- storage and maintenance are the user's responsibility

### Option 2: AWS RDS

Pros:

- managed backups and patching
- stronger production posture
- better isolation from the app host
- easier future scaling path

Cons:

- can create ongoing AWS charges
- requires more networking and security group setup
- adds operational complexity before the demo needs it

### Option 3: SQLite Only

Pros:

- simplest possible local database
- no database service required
- useful for development and tests

Cons:

- less realistic for a deployed API
- not as representative of production analytics systems
- weaker portfolio signal for cloud deployment

## Why the Postgres Container Was Chosen

The Postgres container keeps the deployment realistic without introducing unnecessary AWS services.

It shows that the project can run with a real relational database, while still keeping the one-EC2 architecture understandable and low cost.

## Tradeoffs Accepted

By not using RDS yet, we accept:

- no managed backups
- no Multi-AZ database resilience
- manual responsibility for the Docker volume

These tradeoffs are acceptable because the current deployment is a demo environment with reproducible seed data, not a system of record.

## Consequences

Positive consequences:

- lower cost risk
- simpler deployment
- database schema stays versioned in the repository
- the app can still use Postgres in the cloud

Negative consequences:

- production database operations are not fully solved
- future live-data collection will need a backup and migration strategy

