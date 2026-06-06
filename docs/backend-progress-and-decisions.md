# Backend Progress and Problem-Solution Log

This document summarizes the backend work completed before moving into the frontend step. It explains the problems we found, the solutions we implemented, and why those choices fit the current goal: a professional German job-search platform where users can find jobs, compare salary/company context, and apply through legitimate source or company pages.

## Product Direction We Aligned On

The platform is no longer just a generic analytics dashboard. The backend now supports a clearer product:

- users search for jobs in Germany, not only tech roles
- the search engine returns related jobs for the role/query
- results show company, location, salary range, salary source/estimate status, and match reasons
- users can open a direct apply or company career URL when available
- listings must come from legal, approved, provider-ready sources
- synthetic seed data is allowed for portfolio/demo usage, but must not be presented as live market coverage

This product direction drove the backend changes below.

## 1. Data Legality Was Unclear

Problem:

- The first backend still referenced sources such as LinkedIn and Kaggle in ways that could look production-ready.
- Scraping or unofficial APIs would create legal and reliability risks.
- A public job-search product needs clear permission to store, serve, and link to listings.

Solution:

- Added source-governance rules that classify approved, blocked, and future provider sources.
- Documented the legal source strategy in `docs/decisions/009-legal-data-and-source-strategy.md`.
- Kept local synthetic German listings for development and portfolio review.
- Added ESCO market-context data for occupation and skill normalization because it is legal and improves search quality without pretending to be job listings.

Why this solution:

- It avoids building the product on unapproved scraping.
- It keeps the backend ready for licensed job providers, company feeds, or official APIs later.
- It gives the frontend enough realistic data to build the workflow safely.

## 2. Job Data Was Too Small and Too Demo-Shaped

Problem:

- The old CSV shape was too narrow for real job providers.
- It lacked fields needed for apply handoff, deduplication, expiry, salary transparency, location filters, and provider ingestion.

Solution:

- Expanded the `JobPosting` contract with provider-ready fields:
  - `source_posting_id`
  - `application_url`
  - `company_career_url`
  - `city`
  - `federal_state`
  - `country`
  - `occupation_group`
  - `experience_level`
  - `employment_type`
  - `salary_period`
  - `salary_is_estimated`
  - `salary_confidence`
  - `posted_at`
  - `expires_at`
  - `last_seen_at`
  - `ingestion_batch_id`
- Expanded the legal synthetic German seed data across multiple sectors: healthcare, logistics, retail, finance, sales, HR, trades, hospitality, education, operations, engineering, and public sector.

Why this solution:

- It lets real provider data map into the backend without bending around the old CSV.
- It gives the frontend meaningful filters and result cards.
- It keeps salary estimates clearly separated from listed salaries.

## 3. Search Was Too Simple

Problem:

- Keyword matching alone did not feel like a real search engine.
- German and English role terms needed to match each other.
- Users need filters, sorting, pagination, relevance, and clear match reasons.

Solution:

- Improved the search service with pagination, sorting, filters, salary range handling, company/employment filters, normalized occupation matching, synonyms, German/English matching, relevance scores, and match reasons.
- Added ESCO-aligned aliases such as `Pflege` for nurse and `Buchhaltung` for accountant.
- Added search quality regression tests for exact-title ranking, expired-job exclusion, salary estimate labeling, and German/English synonyms.

Why this solution:

- It protects the core product experience before frontend work begins.
- It makes search explainable to users.
- It prevents future search changes from silently breaking relevance.

## 4. Search Read Directly From CSV/In-Memory Data

Problem:

- The backend could not behave like a serious application while search depended on raw CSV memory.
- Deduplication, expiry, query-by-ID, and provider ingestion needed a repository layer.

Solution:

- Added `JobPostingRepository`.
- Added repository support for saving normalized provider results, deduplication by `source + source_posting_id`, active job queries, filtered search, job detail lookup, and similar jobs.
- Moved search behavior toward repository-backed access instead of raw CSV-only logic.

Why this solution:

- It creates a stable persistence boundary.
- It prepares the backend for real providers and scheduled ingestion.
- It lets frontend pages use stable job IDs and detail/apply routes.

## 5. Ingestion Was Split Across API, Pipeline, and Provider Code

Problem:

- Provider fetching, validation, source policy, repository persistence, and expiry marking were not one coherent backend process.
- Relying only on an HTTP route for ingestion is not good operational design.

Solution:

- Added `IngestionService` as the orchestration layer.
- Added an admin CLI:

```bash
python -m src.data_pipeline.ingest --source legal_demo_csv --keyword Nurse --limit 25
python -m src.data_pipeline.ingest --source legal_demo_csv --keyword Nurse --limit 25 --dry-run
python -m src.data_pipeline.ingest --source legal_demo_csv --keyword Nurse --limit 25 --mark-expired
```

- Kept `/data/fetch` protected and hidden from OpenAPI.
- Added ingestion batch persistence through `ingestion_batches`.

Why this solution:

- The same ingestion path can be used by CLI, cron, GitHub Actions, Airflow, or a future scheduler.
- Ingestion is auditable.
- Source governance cannot be bypassed by calling a different path.

## 6. Operational Routes Were Too Public

Problem:

- `/data/fetch` was too sensitive to be treated like a normal public route.
- Public deployments need CORS, rate limits, request logging, and clear health checks.

Solution:

- Hid `/data/fetch` from OpenAPI.
- Protected ingestion with `X-Admin-Token` and `INGESTION_API_TOKEN`.
- Added explicit CORS origins instead of wildcard defaults.
- Added per-client rate limiting.
- Split `/health` and `/ready`.
- Added request logging and request IDs.

Why this solution:

- Public users can search and apply, but cannot trigger backend ingestion.
- Deployment probes can distinguish liveness from dependency readiness.
- Debugging public issues becomes easier.

## 7. Errors Were Not Consistent

Problem:

- Some endpoints returned FastAPI default errors.
- Some returned custom details.
- The frontend would need special parsing for every error path.

Solution:

- Added a standard backend error contract:

```json
{
  "error": "source_policy_violation",
  "message": "...",
  "details": {}
}
```

- Applied it to blocked ingestion, missing jobs, validation failures, rate limits, repository errors, and unexpected errors.

Why this solution:

- The frontend can handle errors predictably.
- Logs and request IDs can be connected to user-facing failures.

## 8. Salary Needed Transparency

Problem:

- Many German job postings do not show salaries.
- If the backend estimates salaries, listed and estimated salaries must never be mixed without clear labeling.

Solution:

- Added salary estimation based on role, location, and experience context.
- Added `salary_is_estimated`, `salary_confidence`, and `salary_period`.
- Added tests to protect salary filtering and labeling behavior.

Why this solution:

- Users still get useful salary context.
- The platform stays honest about what is listed data and what is estimated intelligence.

## 9. Database Changes Needed Control

Problem:

- `create_all` is fine for quick local setup but not enough for serious schema evolution.
- Provider-ready job fields, indexes, and batch tables need reviewable migrations.

Solution:

- Added Alembic migrations.
- Added initial schema migration, provider-readiness migration, and ingestion batch audit migration.
- Added migration commands to README and Makefile.
- Kept a SQLite compatibility shim only for local development convenience.

Why this solution:

- Deployed databases can evolve safely.
- Indexes and constraints are explicit.
- Future backend changes do not depend on accidental local schema creation.

## 10. Deployment Config Could Be Dangerous

Problem:

- Bad config should fail at startup, not become a public security issue.
- Examples: wildcard CORS in production, enabled ingestion without a token, invalid database URL, weak rate limits, or missing production data.

Solution:

- Added startup validation in settings.
- Added `INGESTION_ENABLED`.
- Rejected unsafe production combinations when `DEBUG=false`.
- Updated `.env.example`, Docker Compose free-tier config, and deploy script with explicit safe values.
- Added tests for config validation.

Why this solution:

- It protects every runtime path, not only one deployment script.
- It makes local, Docker, EC2, and future scheduled jobs follow the same configuration contract.

## 11. Observability Was Too Basic

Problem:

- If redeployment breaks, plain logs are not enough.
- Ingestion and API failures need request IDs and structured events.

Solution:

- Added centralized logging setup.
- Added request ID middleware.
- Added error logging middleware.
- Added structured ingestion events.
- Added `LOG_JSON=true` deployment support.

Why this solution:

- Operators can connect a user-facing error to backend logs.
- Ingestion jobs become easier to debug.
- JSON logs are ready for future log collection.

## 12. Backend Readiness Before Frontend

Current backend readiness:

- Provider-ready job model exists.
- Repository layer exists.
- Search engine is meaningful and tested.
- Legal source policy exists.
- Ingestion service and admin CLI exist.
- Ingestion batches are persisted.
- API schemas and error contract are explicit.
- Public backend guardrails exist.
- Deployment config validation exists.
- Alembic migrations exist.
- Final backend review is documented in `docs/backend-review-2026-06-06.md`.

Known remaining backend items:

- Run Docker validation on a machine where Docker is available.
- Add deployment migration execution before API startup.
- Run one live redeployment smoke test.
- Decide whether public OpenAPI docs should stay enabled for portfolio review.
- Move rate limiting to Redis or an edge layer only if the app scales beyond one process.

## Why We Are Ready For Frontend

The frontend can now build against a stable backend contract:

- search endpoint
- filters and facets
- job detail endpoint
- similar jobs endpoint
- apply handoff endpoint
- legal data governance endpoint
- standard error response shape
- salary estimate/listed salary flags
- match reasons and relevance scores

That is enough to build the first real product UI: search jobs in Germany, filter results, inspect job detail, and apply through the source or company page.
