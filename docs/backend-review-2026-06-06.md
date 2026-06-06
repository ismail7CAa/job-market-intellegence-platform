# Backend Review - 2026-06-06

This review captures the backend state before frontend polish and redeployment. The goal is to make the remaining backend risks explicit: public API surface, source legality, repository persistence, deployment configuration, Docker runtime, and test coverage.

## Summary

The backend is now much closer to a real job-search platform than the first portfolio version. Search reads through a repository, ingestion is source-governed, job postings have provider-ready fields, ingestion batches are auditable, errors follow one response contract, and deployment settings fail fast when unsafe.

The next backend work should be hardening rather than feature invention: run migrations in the deployment path, verify production environment variables on the EC2 host, and keep search relevance protected with regression tests as the frontend grows.

## Endpoint List

Public product routes:

- `GET /`
- `GET /jobs/search`
- `GET /jobs/search/facets`
- `GET /market/esco/normalize`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/similar`
- `GET /jobs/{job_id}/apply`
- `GET /data/governance`
- `GET /engine/workflow`
- `POST /analyze/skills`
- `GET /trends/skills`
- `GET /skills/{skill_name}/salary-premium`
- `GET /skills/{skill_name}/related`
- `GET /predict/roles`
- `GET /salary/anomalies`
- `GET /report/skill-demand`
- `GET /export/skills-csv`
- `GET /status/pipeline`
- `GET /stats/jobs`

Operational public probes:

- `GET /health`: liveness only
- `GET /ready`: dependency readiness for database and loaded job data

Protected/internal routes:

- `POST /data/fetch`: hidden from OpenAPI and protected with `X-Admin-Token` when `INGESTION_API_TOKEN` is configured. It still applies source-policy checks after authentication.

## Public, Protected, And Internal Route Review

The current split is acceptable for a single-instance portfolio deployment:

- Read-oriented search, job detail, apply handoff, governance, and analytics routes are public.
- Health and readiness are public but exempted from rate limiting for deployment probes.
- Ingestion is not part of the anonymous public surface.
- Rate limiting applies to public routes using the configured request/window settings.
- Errors use `{"error": "...", "message": "...", "details": {}}`, which is ready for frontend handling.

Remaining risk:

- If the service grows beyond one process, the in-memory rate limiter should move to Redis, an API gateway, or WAF rules.
- `/docs` remains available by FastAPI default. That is acceptable for portfolio review, but production could disable or protect OpenAPI docs.

## Legal Data Policy

Current policy:

- Local committed job listings are synthetic German seed data.
- ESCO is used as legal market-context data for occupation and skill normalization.
- Unapproved sources such as legacy LinkedIn/Kaggle adapters are blocked by source governance for production ingestion.
- `/data/governance` explains the current source policy to API consumers.

This is legally safer than scraping or using unofficial endpoints. The backend is ready to plug in licensed providers or company feeds through the provider adapter interface without changing the search engine.

Remaining risk:

- The product should not claim live German market coverage until a licensed provider, official API with clear terms, or explicit company feed is connected.

## Repository And Database Review

Repository state:

- `JobPostingRepository` handles persistence, deduplication by `source + source_posting_id`, active job queries, filtered search, detail lookup, and similar jobs.
- `IngestionBatchRepository` persists ingestion batch lifecycle state.
- `IngestionService` owns the provider-backed ingestion path used by both `/data/fetch` and the admin CLI.

Indexes and constraints:

- `job_postings` indexes searchable and filterable columns: title, company, location, city, federal state, source, source posting ID, remote status, role type, occupation group, experience level, ingestion batch, posted/expiry/last-seen timestamps, and expired state.
- `job_postings` has a uniqueness constraint on `source + source_posting_id`.
- `ingestion_batches` indexes status and started timestamp.
- Skill trend tables keep their skill/month uniqueness constraint.

Remaining risk:

- SQLite compatibility shims are useful locally, but deployed schema changes should use Alembic migrations.
- If search volume grows, relevance ranking may need database-backed full-text search instead of Python scoring over repository results.

## Admin CLI For Repository-Backed Ingestion

Status: implemented.

Command examples:

```bash
python -m src.data_pipeline.ingest --source legal_demo_csv --keyword Nurse --limit 25
python -m src.data_pipeline.ingest --source legal_demo_csv --keyword Nurse --limit 25 --dry-run
python -m src.data_pipeline.ingest --source legal_demo_csv --keyword Nurse --limit 25 --mark-expired
```

The CLI uses `IngestionService`, `JobPostingRepository`, and `IngestionBatchRepository`, so it follows the same governance, validation, persistence, expiry, and batch-audit path as the protected API route.

## Test Coverage Review

Current useful coverage:

- API response and security behavior
- repository-backed search and job detail behavior
- ingestion service and ingestion CLI
- ingestion batch persistence
- database repository behavior
- Alembic migration chain
- search quality regressions for German/English terms, ranking, salary type, and expiry
- deployment config validation
- ESCO market-context normalization
- analytics and ML experiment workflows

Latest local result during this backend hardening pass:

```text
117 passed, 2 warnings
```

Remaining risk:

- Add deployment smoke tests once the EC2 app is redeployed.
- Add one integration test that runs migrations against a temporary database, starts the app, and verifies `/ready`, `/jobs/search`, and `/data/governance`.

## README Setup Review

README now documents:

- runtime `.env` setup through `.env.example`
- admin repository ingestion commands
- Alembic migration commands
- public/protected route split
- public backend guardrails
- source/legal data strategy
- deployment status and remaining production hardening

This is enough for a reviewer or future maintainer to understand how to run, test, ingest, migrate, and deploy the backend.

## Deployment Env Vars Review

Deployment now has fail-fast validation for:

- `CORS_ALLOW_ORIGINS=["*"]` with `DEBUG=false`
- `INGESTION_ENABLED=true` without `INGESTION_API_TOKEN`
- invalid or unsupported `DATABASE_URL`
- non-positive or overly permissive rate-limit settings
- missing `PRODUCTION_DATA_PATH` when `DEBUG=false`

The EC2 Docker Compose path now sets explicit safe runtime values for public base URL, CORS, ingestion enablement, rate limits, JSON logs, and data paths.

Remaining risk:

- If ingestion is enabled on a public host, `INGESTION_API_TOKEN` must be a strong secret and should be stored outside Git.
- If a custom domain or HTTPS proxy is added, `PUBLIC_BASE_URL` and `CORS_ALLOW_ORIGINS` must be updated to match the real frontend origin.

## Docker Runtime Review

Current Docker posture:

- multi-stage image
- runtime dependencies split into `requirements-runtime.txt`
- non-root application user
- healthcheck against `/health`
- slim Python base image
- one-EC2 compose path with local Postgres for low-cost portfolio deployment

Remaining risk:

- The compose startup path should run `alembic upgrade head` before launching the API once deployment persistence is used as the source of truth.
- `/ready` would be a better rollout check than `/health` for deployment automation, while `/health` remains fine for container liveness.

## Recommended Next Backend Steps

1. Add a deployment migration step before API startup.
2. Run one EC2 redeployment smoke test with `DEBUG=false`, explicit CORS origin, JSON logs, and readiness checks.
3. Decide whether OpenAPI docs should remain public for portfolio review or be disabled in deployment.
4. Add a small integration smoke test around migrations plus `/ready` and `/jobs/search`.
5. Move rate limiting to Redis or an edge layer only if the backend scales beyond one process.
