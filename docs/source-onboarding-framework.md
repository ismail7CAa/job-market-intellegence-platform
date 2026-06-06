# Source Onboarding Framework

This document explains how the backend decides whether a job listing source can be used by the platform.

## Problem

The platform is becoming a German job-search and apply engine. That means source handling cannot be casual:

- a provider may allow search but not storage
- a job board may expose public pages but still prohibit automated ingestion
- a dataset may be downloadable but not redistributable
- an apply URL may belong to the provider, the employer, or neither
- repeated ingestion needs a stable deduplication key

Hardcoding source names in one policy function was a good first guardrail, but it was not enough for a professional backend. Hiring teams and future maintainers need to see the source lifecycle explicitly.

## Solution

We added a source onboarding registry at:

- `config/source_registry.json`

The registry stores:

- source id
- display name
- source type
- allowed or blocked status
- approval status
- legal basis
- required action
- whether listings can be stored
- whether listings can be displayed
- whether apply links can be used
- whether a contract or permission record is required
- refresh policy
- deduplication key
- expiry policy
- product use case

The policy function still exposes the same simple code interface:

```python
evaluate_source("company_feed")
```

But the decision now comes from structured registry data instead of only a hardcoded set.

## Why JSON

The registry uses JSON because it is:

- supported by Python's standard library
- easy to validate in tests
- easy to inspect in GitHub reviews
- dependency-free for Docker and CI

YAML would also work, but the project does not currently need another parser dependency.

## Why Python Dataclasses

The source registry is loaded into dataclasses in `src/data_pipeline/source_policy.py`.

Dataclasses are enough here because:

- the registry is internal configuration
- the fields are simple and stable
- tests cover the expected entries
- the API response still uses Pydantic schemas at the public boundary

Pydantic remains the right tool for API contracts. Dataclasses are lighter for internal configuration.

## Why FastAPI Endpoint Plus CLI

Two visibility paths were added:

- `GET /data/sources`
- `python -m src.data_pipeline.sources`

The endpoint helps the frontend, portfolio reviewers, and API clients understand source readiness. The CLI helps operators inspect the same policy without starting the web server.

This is intentional. Source governance is both a product concern and an operations concern.

## Current Source Strategy

Approved or conditionally approved paths:

- `legal_demo_csv`: current legal portfolio seed listings
- `local_csv`: local development data
- `company_feed`: allowed only when explicit employer permission is documented
- `licensed_provider`: allowed only when the provider contract permits the platform use case
- `official_api`: allowed only when official terms permit listing storage, search, display, and apply-link handoff

Blocked by default:

- `linkedin`
- `stepstone`
- `indeed`
- `glassdoor`
- `kaggle`
- `scraper`
- `web_scraping`
- `unapproved_api`

LinkedIn and StepStone are not blocked because they are bad sources. They are blocked because scraping or unofficial access would create legal and maintenance risk. They can be added later through official partner/API access, a feed contract, or written permission.

## Provider Example

`MockCompanyFeedProvider` was added as a permissioned company-feed example.

It is synthetic and uses `.example.com` URLs, but it proves the real backend shape:

- stable `source_posting_id`
- explicit `source_legal_basis`
- `application_url`
- `company_career_url`
- salary metadata
- lifecycle timestamps
- location breakdown
- occupation group and experience level

This lets ingestion, repository deduplication, search, apply handoff, and source governance exercise a realistic employer-feed path without using real unlicensed data.

## How To Inspect Sources

CLI:

```bash
python -m src.data_pipeline.sources
python -m src.data_pipeline.sources --source stepstone
python -m src.data_pipeline.sources --approved-only
python -m src.data_pipeline.sources --format json
```

API:

```bash
curl http://localhost:8000/data/sources
```

## How To Add A Real Source

1. Confirm the source terms allow the exact product use case.
2. Add or update an entry in `config/source_registry.json`.
3. Implement a `JobPostingProvider` adapter.
4. Normalize every listing into `JobPosting`.
5. Include `source_posting_id`, `application_url`, `source_legal_basis`, `posted_at`, `expires_at`, and `last_seen_at`.
6. Add repository ingestion tests for deduplication and expiry behavior.
7. Add source-policy tests showing why the source is approved.
8. Document the provider decision in an ADR.

No source should be approved only because it is technically fetchable.
