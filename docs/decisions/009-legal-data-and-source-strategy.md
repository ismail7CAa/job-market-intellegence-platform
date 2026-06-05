# ADR 009: Legal Data and Source Strategy for the German Job Search Engine

- Status: Accepted
- Date: 2026-06-05

## Context

The product direction changed from a generic analytics dashboard into a job-search engine for Germany:

> search for any job in Germany, inspect matching roles, compare salary and company context, then apply through the original employer or approved source page.

That shift makes the data strategy much more important. A dashboard can be honest with a small reproducible dataset. A search engine immediately raises harder questions:

- Are the jobs real or demo records?
- Are the listings current?
- Do we have permission to store and serve them?
- Can users click through to a legitimate apply page?
- Can the platform scale beyond a tiny CSV without using unapproved scraping?

The first implementation had an important weakness: old source names such as LinkedIn and Kaggle were still present in code and tests, and the public product story could be read as if the platform had live production-grade job listings. That is not acceptable for a serious backend.

## Research Findings

### 1. Bundesagentur fuer Arbeit job listings

The Bundesagentur fuer Arbeit has the official public Jobsuche portal. It is the natural first place to look for Germany job listings.

However, the commonly referenced jobsuche API documentation is community-maintained, not official. The bundesAPI project explicitly states that the Bundesagentur fuer Arbeit does not provide an official API for the Jobsuche listings dataset.

Decision impact:

- We should not build production ingestion on the unofficial Jobsuche endpoint.
- We may link users to Bundesagentur search/apply pages as an external source URL.
- We may use official BA statistics APIs for aggregate labour-market context.

Reference:

- Community Jobsuche API note: https://github.com/bundesAPI/jobsuche-api
- Official BA statistics API start page: https://statistik.arbeitsagentur.de/DE/Navigation/Service/API/API-Start-Nav.html
- Official BA reported-vacancies statistics API example: https://statistik.arbeitsagentur.de/DE/Statischer-Content/Service/API/API-STEA.html

### 2. Eurostat job vacancy statistics

Eurostat provides free API access to statistical datasets. Its reuse policy allows statistical data reuse for commercial or non-commercial purposes when the source is acknowledged.

Eurostat also publishes job vacancy statistics and describes job vacancies as unmet labour demand. The data is statistical, not individual job postings.

Decision impact:

- Eurostat is a strong no-cost legal source for market context.
- It can support dashboards such as vacancy rate by country, region, industry, or occupation where available.
- It cannot replace a job-listing provider because it does not give application URLs or job descriptions.

References:

- Eurostat API introduction: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction
- Eurostat free reuse notice: https://ec.europa.eu/eurostat/help/copyright-notice
- Eurostat job vacancies information: https://ec.europa.eu/eurostat/web/labour-market/information-data/job-vacancies

### 3. EURES job vacancy statistics and portal

EURES is the European employment-services network and portal. It covers many countries and job vacancies from European public employment services. Its portal help pages state that vacancy data is updated daily and that postings usually come from national job vacancy databases. EURES also exposes public statistics visualisations with downloadable tables based on standard code lists such as NUTS and ESCO.

Decision impact:

- EURES statistics are useful as a legal, no-cost market-context source.
- EURES portal listings are relevant for users, but automated ingestion still needs a confirmed official API or explicit terms allowing the intended use.
- We should not scrape EURES listing pages until the data access and reuse terms are reviewed.

References:

- EURES job vacancy statistics: https://eures.europa.eu/eures-services/eures-portal-statistics/job-vacancy-statistics_en
- EURES help and job vacancy information: https://eures.europa.eu/eures-services/help-and-support_en
- European Labour Authority EURES overview: https://www.ela.europa.eu/en/activities/eures

### 4. ESCO occupation and skill taxonomy

ESCO is the European multilingual classification of skills, competences, qualifications, and occupations. It can be downloaded free of charge in many languages and is available through APIs.

Decision impact:

- ESCO is excellent for normalizing job titles, occupation groups, and skills.
- ESCO is not a job postings dataset.
- It should be used to improve search, similar-job ranking, role categories, and skill extraction.
- The first implementation uses an ESCO-aligned seed vocabulary for the current synthetic corpus and exposes the normalization boundary. Official ESCO concept URIs can be added once the official ESCO export is loaded into the project.

References:

- ESCO download page: https://esco.ec.europa.eu/en/use-esco/download
- ESCO overview: https://employment-social-affairs.ec.europa.eu/policies-and-activities/skills-and-qualifications/skills-jobs/european-skillscompetences-qualifications-and-occupations-esco_en
- ESCO API page: https://esco.ec.europa.eu/en/use-esco/use-esco-services-api

### 5. Free third-party job datasets and scraping projects

There are many third-party job datasets, scraping projects, and free samples. They may be useful for experimentation, but they are not automatically safe for a public product.

Decision impact:

- A dataset is not approved just because it is downloadable.
- Before ingestion, we need clear license terms, source permission, refresh rules, redistribution rights, and apply-link handling.
- Reddit posts, unofficial APIs, and scraped datasets should remain blocked unless terms are explicitly verified.

## Decision

Use a two-layer data strategy:

### Layer 1: Job Listings

For actual searchable job listings shown to users, allow only:

- local legal demo data
- licensed job-data providers
- explicit company career feeds
- official APIs that clearly allow the intended listing use

These records must normalize into the `JobPosting` contract and include source-governance metadata.

### Layer 2: Market Context

For broader labour-market intelligence, allow official open statistical and taxonomy sources:

- Eurostat job vacancy statistics
- Bundesagentur fuer Arbeit statistics APIs
- EURES vacancy statistics downloads
- ESCO occupation and skill taxonomy

These sources should enrich the product but not pretend to be individual job listings.

## What We Changed in the Backend

The backend was changed to enforce this strategy:

- Added `src/data_pipeline/source_policy.py`.
- Added `src/data_pipeline/providers.py`.
- Added a `JobPostingProvider` adapter interface.
- Default source changed to `legal_demo_csv`.
- `/data/fetch` now blocks unapproved sources such as LinkedIn and Kaggle.
- `/data/fetch` is hidden from OpenAPI and requires `X-Admin-Token` when `INGESTION_API_TOKEN` is configured, so ingestion is not part of the anonymous public surface.
- `/data/governance` exposes the current source policy and legal basis.
- `/engine/workflow` describes the product workflow from search intent to apply handoff.
- `/jobs/{job_id}/apply` centralizes the apply handoff so the frontend does not invent apply behavior.
- Public job APIs now use explicit Pydantic response schemas.
- The public AI-agent endpoints were removed because they did not support the core job-search/apply workflow.
- CORS now defaults to explicit local frontend origins rather than a wildcard.
- Public requests now pass through basic request logging and a per-client rate limiter.
- `/health` is a cheap liveness probe, while `/ready` checks database and loaded job-data readiness.
- Added `IngestionService` to orchestrate provider fetches into the repository with source governance, validation, deduplication, expiry marking, and batch summaries.
- Added `python -m src.data_pipeline.ingest` so approved ingestion can run from an admin CLI, cron, GitHub Actions, or a future scheduler without depending on `/data/fetch`.
- Added Alembic migrations so database schema changes are controlled instead of relying only on SQLAlchemy `create_all`.
- Added structured observability: JSON-capable Loguru configuration, request IDs, request/error events, and ingestion batch events.
- Added a standard API error contract: `error`, `message`, and `details`.
- Added search quality regression tests for German/English synonyms, exact-title ranking, salary-type labeling, and expired-listing exclusion.

## Problems Found During Backend Hardening

Several implementation problems appeared once the platform goal became a real job-search and apply engine instead of a dashboard:

### 1. Search was coupled to CSV memory

The search service still read serialized jobs from the in-memory pipeline. That was acceptable for a small local dashboard, but it was not a good backend boundary for provider data.

Problems:

- provider results could not be persisted independently of the CSV fallback
- duplicate listings from repeated ingestion batches were hard to prevent
- job detail, similar jobs, facets, and apply handoff all depended on process memory
- a restart could change behavior depending on whether the CSV had already been loaded

Decision:

- Add `JobPostingRepository` as the storage and query boundary.
- Keep the legal CSV as a fallback seed source, but ingest it through the same repository path used by future providers.
- Make the search service read from the repository first, with the in-memory loader kept only as a fallback for tests and non-database modes.

### 2. Provider identity was missing from persistence

Real job providers usually expose a stable provider-side posting ID. Without storing that identity, the platform would have to guess whether two records were the same job.

Problems:

- repeated provider pulls could create duplicate jobs
- source updates could not cleanly overwrite existing records
- apply links and salary fields could drift across ingestion batches

Decision:

- Store `source_posting_id`.
- Deduplicate by `source + source_posting_id`.
- Keep the platform `id` as the internal API identifier.

### 3. Ingestion was exposed too broadly

The fetch route is useful for local development and controlled provider ingestion, but it is not a public product feature. A public visitor should be able to search jobs, inspect job details, understand source governance, and open an apply link. They should not be able to trigger ingestion.

Problems:

- `/data/fetch` appeared in OpenAPI next to user-facing search routes
- anonymous callers could reach a write-like operational action
- source governance blocked bad sources, but authentication and route visibility were still too weak for redeployment

Decision:

- Hide `/data/fetch` from OpenAPI.
- Require `X-Admin-Token` backed by `INGESTION_API_TOKEN`.
- Return `404` when no ingestion token is configured, so the route is closed by default.
- Keep source-governance checks after authentication, because an admin token should not bypass legal-source policy.

### 4. Public backend guardrails were missing

The backend had grown from a portfolio analytics API into a job-search and apply engine. Before redeployment, the public surface needed basic operational controls.

Problems:

- CORS defaulted to `*`, which is too permissive for a public deployment
- there was no rate limit for anonymous routes
- request behavior was not logged consistently
- `/health` mixed liveness and dependency readiness, which makes deployment checks harder to reason about

Decision:

- Default CORS to explicit localhost development origins and require deployment-specific frontend origins through configuration.
- Add simple in-memory rate limiting for the current single-instance EC2 deployment.
- Add request logging for method, path, status, client IP, and duration without logging search text or query details.
- Keep `/health` as liveness and add `/ready` for database plus job-data readiness.

Not chosen yet:

- Full authentication for every endpoint. The current product surface is read-heavy and intended to be publicly browsable.
- Redis-backed distributed rate limiting. That becomes necessary when the API scales beyond one instance.
- API gateway or WAF rules. Those are useful production controls, but they add infrastructure before the single-instance backend contract is stable.

### 5. Observability needed structure before redeployment

Basic text request logs are useful locally, but they are not enough when a public backend breaks after redeployment. The backend needs correlation between user requests, errors, and ingestion batches.

Problems:

- request logs did not include a stable request identifier
- unhandled errors could be hard to connect to a user-facing response
- ingestion batches emitted useful summaries, but not structured operational events
- deployment log collection benefits from JSON logs

Decision:

- Add centralized Loguru configuration with `LOG_JSON=true` for serialized deployment logs.
- Accept or generate `X-Request-ID`, return it on every response, and include it in request/error logs.
- Add error logging in middleware for unhandled API exceptions.
- Emit structured ingestion events for batch start, blocked sources, provider fetch/results, and batch completion.
- Keep search query strings out of request logs to avoid unnecessary user-input logging.

Not chosen yet:

- A public `/metrics` endpoint. Metrics are useful, but should be designed with access control and deployment monitoring in mind.
- A full tracing system. Request IDs give us the first level of correlation without adding external infrastructure.

### 6. API errors needed one frontend contract

FastAPI's default error shape uses `detail`, while several custom endpoints had nested dictionaries with their own conventions. That is awkward for the frontend and for debugging because every error path needs special parsing.

Problems:

- blocked ingestion returned a custom object inside `detail`
- rate limiting returned a plain string inside `detail`
- missing jobs returned plain strings
- request validation returned FastAPI's default validation shape
- repository outages and unexpected errors were not normalized

Decision:

- Add a standard error contract: `{"error": "...", "message": "...", "details": {}}`.
- Add an `ErrorResponse` schema and expose it in OpenAPI.
- Add HTTP and validation exception handlers that normalize legacy exceptions.
- Use explicit error codes for source-policy violations, missing jobs, validation failures, rate limits, repository unavailability, and internal errors.
- Include request IDs in error details when useful for log correlation.

Not chosen:

- Preserve FastAPI's default `detail` envelope. It is convenient for framework defaults, but less clean for a product frontend.
- Return stack traces or raw validation text to public clients. Those details belong in structured logs, not public responses.

### 7. Search quality needed regression protection

Once search started using ESCO enrichment, salary estimation, repository filtering, and relevance scores, it became possible to break useful behavior without breaking response schemas.

Problems:

- German occupation terms such as `Pflege` and `Buchhaltung` need to keep matching their English canonical roles
- exact title matches should outrank weak description mentions
- salary filters may include estimated salaries, but listed and estimated salaries must remain clearly marked
- expired jobs must not leak back into user-facing search
- match reasons should explain the strongest match, not only the first internal signal

Decision:

- Add dedicated search quality regression tests.
- Add `Pflege` to the local ESCO nurse aliases.
- Keep exact title match reasons first when a query directly hits the job title.

### 8. Ingestion needed one orchestration path

After the provider interface and repository were added, ingestion still risked splitting across too many places. `DataPipeline` could fetch provider records and optionally publish to Kafka. `/data/fetch` could trigger fetching. `JobPostingRepository` could persist records. But there was no single service responsible for turning an approved provider refresh into the searchable repository state.

Problems:

- the protected API route was starting to contain ingestion workflow logic
- provider adapters, validation, repository persistence, and expiry marking were not tied together as one backend process
- future scheduler or CLI ingestion would have duplicated route logic
- ingestion results needed a stable batch summary for logs, tests, and admin visibility

Decision:

- Add `IngestionService`.
- Run source governance before fetching.
- Fetch through `JobPostingProvider`.
- Attach an `ingestion_batch_id` and `last_seen_at`.
- Validate provider results with the Pandera job-posting schema before persistence.
- Save through `JobPostingRepository`, preserving deduplication by `source + source_posting_id`.
- Mark expired jobs after refresh when requested.
- Return a batch summary with fetched, saved, expired, active-job, provider, and timing fields.
- Expose the same process through an admin CLI with `--source`, `--keyword`, `--limit`, `--dry-run`, and `--mark-expired`.

Not chosen:

- Put this logic inside `/data/fetch`. That would make the API route too responsible and harder to reuse from a scheduler.
- Put this logic inside `DataPipeline`. That class still owns broader pipeline concerns such as CSV exports and optional Kafka publishing; repository refresh is now a product-serving concern.
- Depend only on an HTTP endpoint for operational ingestion. Scheduled backend jobs should be able to run without public routing, CORS, or admin-token headers.

### 9. Expired listings needed explicit state

`expires_at` alone tells us when a job should no longer appear, but user-facing queries need a simple active/expired filter.

Problems:

- every query would need to recalculate expiry rules
- expired jobs could accidentally remain visible in search results
- detail lookup and similar-job lookup needed the same active-listing rule

Decision:

- Add `is_expired`.
- Add repository-level `mark_expired`.
- Exclude expired jobs from default search, detail, facets, and similar-job queries.
- Do not auto-expire the local seed dataset on app startup, because the portfolio seed has fixed historical dates and would otherwise disappear during demos. Live provider refresh jobs can call `mark_expired` after each ingestion run.

### 10. Similar jobs needed persisted matching signals

The existing similarity logic used role type, location, remote status, and required skills. The SQL model did not persist `required_skills`, so moving search into the repository would have dropped an important matching signal.

Decision:

- Persist `required_skills` as compact JSON text for the repository stage.
- Keep a future normalized `job_skills` relation available for deeper analytics and ESCO enrichment.

### 11. Database changes needed real migrations

The backend now has a provider-ready job model, repository queries, protected ingestion, and apply-handoff behavior. At that point, database schema changes are no longer a casual local concern. A public deployment needs repeatable migrations.

Problems:

- `Base.metadata.create_all` creates missing tables but does not reliably evolve existing schemas
- the SQLite compatibility shim is useful for local development, but it is not a deployment migration strategy
- indexes and uniqueness constraints need to be explicit and reviewable
- future production databases need a clear command for schema upgrades

Decision:

- Add Alembic configuration under `alembic.ini` and `migrations/`.
- Create an initial core schema migration.
- Create a second job-posting provider-readiness migration for provider fields, active/expired state, indexes, and `source + source_posting_id` uniqueness.
- Add README and Makefile commands for `alembic upgrade head` and autogenerated revisions.
- Keep the SQLite shim only as a development compatibility aid for old local databases.

### 12. Local SQLite schemas drifted from the SQLAlchemy model

Existing developer SQLite databases are not automatically changed by `create_all` when new columns are added. After adding provider-ready fields, older local databases could crash with missing-column errors.

Decision:

- Add a small SQLite compatibility shim that adds missing job-posting columns for local development.
- Keep PostgreSQL bootstrap schema in `database/init.sql` aligned with the SQLAlchemy model.
- Treat this as a development convenience, not a replacement for proper migrations once production persistence is introduced.

## Why We Did Not Choose Other Solutions

### Not unapproved scraping

Scraping job boards would give more rows quickly, but it creates terms-of-service, rate-limiting, reliability, and ethical risks. It also makes the product fragile because HTML structures change without warning.

Rejected for now.

### Not the unofficial Bundesagentur Jobsuche API

The unofficial endpoint is attractive because it appears to expose the right data. But the available documentation is community-maintained and explicitly says there is no official Jobsuche API.

Rejected for production ingestion.

### Not Kaggle as a default source

Kaggle can be useful for experiments, but generic job datasets are often stale, not Germany-specific, and inconsistently licensed. They also usually lack reliable apply URLs.

Rejected as default product data.

### Not a paid provider yet

A licensed job-data provider may become the best production answer. But choosing one before the backend contract is stable would couple the product too early to a vendor.

Deferred until provider terms, cost, and coverage are reviewed.

## Recommended Next Data Improvements

The current committed dataset is broader than the first seed, but it is still synthetic and should not be presented as live market coverage. Before frontend polish or redeployment, improve the data story in this order:

1. Load the official ESCO export and populate `esco_occupation_uri` / skill concept URIs.
2. Add `language_requirements` once language extraction is implemented.
3. Add Eurostat or BA statistics as market-context endpoints, clearly separate from job listings.
4. Add a provider adapter only after the source terms are confirmed.

Completed on 2026-06-05:

- provider-ready listing fields were added to `JobPosting`
- seed CSVs now include source posting IDs, application URLs, company career URLs, location breakdown, salary metadata, occupation group, experience level, employment type, lifecycle timestamps, and ingestion batch IDs
- the legal synthetic German seed dataset was expanded to 120 production listings and 120 training listings
- the seed dataset now covers healthcare, logistics, retail, finance, sales, HR, construction and trades, hospitality, education, operations, engineering, and public sector roles across German cities
- validation, API schemas, SQLAlchemy model, and database init SQL were aligned with the expanded listing contract
- repository-backed search was added through `JobPostingRepository`
- provider results can now be saved, deduplicated by source identity, marked expired, queried by filters or ID, and matched to similar jobs
- the search service now reads from the repository first instead of treating the CSV pipeline as the primary search index
- ESCO market-context normalization was added for occupation and skill aliases
- `/market/esco/normalize` exposes query normalization, and search ranking uses ESCO-expanded terms without treating ESCO as a listing source
- `/jobs/search` now supports pagination, sorting, company filters, role-type filters, salary range filters, employment-type filters, relevance scores, and match reasons
- search matching now combines direct text matches, normalized occupation matches, skill matches, and ESCO-backed German-English synonym matches
- salary estimation was added for postings without listed pay, using role type, location, occupation group, and experience-level peers
- estimated salaries are never presented as listed salaries; API responses include `salary_type=estimated`, `salary_is_estimated=true`, confidence, and estimation basis

## Source Approval Matrix

| Source | Cost | Legal posture | Individual job listings? | Apply URLs? | Backend use |
| --- | --- | --- | --- | --- | --- |
| Local legal seed CSV | Free | Approved for portfolio seed use | Yes, synthetic seed listings | Yes, source links | Current default |
| Company career feeds with permission | Free or negotiated | Approved when permission is explicit | Yes | Yes | Future provider |
| Licensed job provider | Usually paid, possibly free tier | Approved if contract allows | Yes | Usually yes | Future provider |
| Bundesagentur Jobsuche public portal | Free for users | Use as external link; no confirmed official listings API | Yes in UI | Yes in UI | Link out only |
| Unofficial Jobsuche API | Free | Not approved for production | Yes | Possibly | Blocked |
| BA statistics API | Free | Official aggregate data | No | No | Market context |
| Eurostat API | Free | Official reusable statistics with attribution | No | No | Market context |
| EURES statistics | Free | Official statistics/download tables | No direct listing contract | No | Market context |
| EURES portal listings | Free for users | Needs terms/API review for ingestion | Yes | Yes | Candidate, not approved |
| ESCO taxonomy | Free | Official taxonomy/API/download | No | No | Enrichment |
| Kaggle/random scraped datasets | Free or mixed | License-specific, often unclear | Sometimes | Usually no | Experiments only |

## Consequences

Positive:

- The project is legally safer.
- The product can still grow beyond demo data through official aggregate sources.
- The provider adapter boundary keeps future live ingestion clean.
- The frontend can be honest about which records are demo, official context, or provider-backed.

Negative:

- We do not yet have a large live job-listing corpus.
- Search results remain limited until a licensed/company provider is added.
- Aggregate statistics cannot replace the apply-focused listing experience.

## Final Position

The backend should stay strict:

- Searchable jobs require an approved listing source.
- Market intelligence can use official open statistics.
- Skill and occupation normalization should use ESCO.
- Unapproved scraping stays blocked.

This is slower than scraping, but it creates a platform that is credible, legal, and easier to maintain.
