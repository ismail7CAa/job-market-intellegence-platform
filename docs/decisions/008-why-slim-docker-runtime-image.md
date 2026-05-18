# ADR 008: Why a Slim Docker Runtime Image

- Status: Accepted
- Date: 2026-05-19

## Context

The first GitHub Actions Docker build failed with:

```text
No space left on device
```

The original `Dockerfile` installed the full `requirements.txt`, which includes heavy experimentation and orchestration tools such as Airflow, dbt, Feast, Torch, Transformers, Prophet, and XGBoost. Those packages are valuable for future project depth, but they are not needed to serve the public FastAPI dashboard on EC2.

The Docker build context also needed tightening so local artifacts such as `.venv`, MLflow outputs, notebooks, and local databases are not copied into the image build.

## Decision

Use a dedicated `requirements-runtime.txt` for the deployed FastAPI image and keep the full `requirements.txt` for broader local experimentation.

The runtime image installs only the dependencies needed for:

- FastAPI serving
- data validation
- analytics
- role prediction inference/training used by the API
- SQLAlchemy/Postgres connectivity
- Kafka client imports used by the pipeline layer

The Dockerfile now installs dependencies globally into `/usr/local` so the non-root `appuser` can import and run them.

## Options Considered

### Option 1: Full `requirements.txt` in Docker

Pros:

- one dependency file for everything
- image has every optional project capability available
- simple mental model

Cons:

- very large image
- slow CI builds
- GitHub runner disk exhaustion
- unnecessary runtime attack surface
- packages like Airflow/dbt/Feast are not needed by the public API container

### Option 2: Dedicated Runtime Requirements

Pros:

- smaller Docker image
- faster CI build
- lower disk pressure on GitHub Actions
- clearer separation between runtime and experimental dependencies
- easier EC2 deployment on a small instance

Cons:

- two dependency files to maintain
- future runtime imports must be added to `requirements-runtime.txt`

### Option 3: Split Services for API, ML, Orchestration, and Feature Store

Pros:

- production-like separation of concerns
- each service can have its own dependency set
- better long-term scalability

Cons:

- too much operational complexity for the first EC2 portfolio demo
- more containers and more CI/CD work
- not needed to prove the deployed API and dashboard

## Why the Slim Runtime Image Was Chosen

The public deployment only needs the API/runtime surface. Heavy data-platform and MLOps tools remain documented and scaffolded, but they should not make the public container fragile or too large.

The slim runtime image keeps the EC2 demo practical while preserving the broader project roadmap.

## Tradeoffs Accepted

By using a separate runtime requirements file, we accept:

- dependency drift must be watched
- CI should continue testing imports that the runtime image depends on
- future features may require updating both files intentionally

Those tradeoffs are acceptable because the alternative was a slow, oversized image that could not reliably build on GitHub Actions.

## Consequences

Positive consequences:

- Docker build fits within GitHub Actions runner disk limits
- deployment is faster and more reliable
- app runs as a non-root user with globally available dependencies
- runtime image better matches the public serving workload

Negative consequences:

- `requirements-runtime.txt` must stay aligned with the deployed app
- optional research/orchestration tools are not present in the API container

