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
- `/data/governance` exposes the current source policy and legal basis.
- `/engine/workflow` describes the product workflow from search intent to apply handoff.
- `/jobs/{job_id}/apply` centralizes the apply handoff so the frontend does not invent apply behavior.
- Public job APIs now use explicit Pydantic response schemas.
- The public AI-agent endpoints were removed because they did not support the core job-search/apply workflow.

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

### 3. Expired listings needed explicit state

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

### 4. Similar jobs needed persisted matching signals

The existing similarity logic used role type, location, remote status, and required skills. The SQL model did not persist `required_skills`, so moving search into the repository would have dropped an important matching signal.

Decision:

- Persist `required_skills` as compact JSON text for the repository stage.
- Keep a future normalized `job_skills` relation available for deeper analytics and ESCO enrichment.

### 5. Local SQLite schemas drifted from the SQLAlchemy model

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
