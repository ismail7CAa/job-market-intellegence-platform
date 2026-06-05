# ADR 004: Why Local Legal Seed Data Is Used for Job Listings

- Status: Accepted, revised
- Original date: 2026-05-16
- Revised date: 2026-06-05

## Context

The platform is now a Germany-focused job-search and market-intelligence product. The main user workflow is:

> search for jobs in Germany -> inspect a job detail page -> compare market context -> apply through the original employer or approved source page.

That workflow needs two different kinds of data:

1. **Individual job listings**  
   These are the records users search and apply from. They need job titles, companies, locations, descriptions, salaries where available, source metadata, and application/source URLs.

2. **Market context**  
   These are official or aggregate datasets used to explain the wider labour market: vacancy statistics, occupation groups, regional demand, skill taxonomies, salary context, and trends.

The first implementation used small local CSV files. The old wording called this simply "demo data." That is no longer precise enough. The project is not trying to keep the backend as a toy demo. It is using local legal seed records for the listing layer while preparing the backend to accept approved live providers later.

## Decision

Keep local legal seed data for individual job listings until an approved listing provider or explicit company feed is available.

The seed listing files are:

- `data/job_postings_training.csv`
- `data/job_postings_production.csv`

These files are not presented as full market coverage. They are a reproducible local dataset used to exercise and test the product workflow:

- search
- facets
- job detail
- similar jobs
- salary display
- apply handoff
- source governance
- analytics and ML experiments

The backend default source is `legal_demo_csv`, but the purpose is now better described as **local legal seed listings**, not as the final data strategy.

For larger no-cost legal data, the platform should use official aggregate/context sources, not pretend those sources are individual job postings:

- Eurostat job vacancy statistics
- Bundesagentur fuer Arbeit statistics APIs
- EURES vacancy statistics
- ESCO occupation and skill taxonomy

The full source strategy is documented in [ADR 009: Legal Data and Source Strategy](009-legal-data-and-source-strategy.md).

## What Changed Since the Original ADR

The original ADR said the public portfolio version used a small German job-market demo dataset. That was accurate for the first dashboard-style version.

The product has since changed:

- It is no longer only about tech jobs.
- It is no longer centered on a generic analytics dashboard.
- It is now centered on job search and apply handoff.
- The public AI-agent surface was removed.
- A provider adapter interface was added.
- Source governance was added.
- The API now has explicit Pydantic response contracts.
- The backend blocks unapproved live sources.

Because of that, the correct framing is:

> Local legal seed listings are used to develop and test the listing workflow. Official open datasets are used for market context. Real live listings require an approved source.

## Options Considered

### Option 1: Keep Local Legal Seed Listings

Pros:

- reproducible in local development and tests
- no credentials required
- no terms-of-service scraping risk
- stable for CI and backend contract tests
- supports search, detail, similar jobs, and apply handoff
- allows product engineering to continue before a provider is selected

Cons:

- not representative of the German labour market
- too small for meaningful market trends
- salaries and demand insights are illustrative
- must be clearly labeled as seed/demo listing data

### Option 2: Use Unapproved Scraping for More Listings

Pros:

- more rows quickly
- fresher-looking search results
- easier to make the product feel populated

Cons:

- terms-of-service and legal risk
- fragile parsers
- blocked requests and rate-limit problems
- unclear redistribution rights
- no reliable long-term source contract
- not appropriate for a serious public product

Decision: rejected.

### Option 3: Use the Unofficial Bundesagentur Jobsuche API

Pros:

- Germany-specific listings
- likely useful fields for search
- attractive because the public Jobsuche portal is official

Cons:

- the commonly referenced API documentation is community-maintained
- available documentation says there is no official Jobsuche listings API
- production use would be hard to justify without confirmed terms

Decision: rejected for production ingestion. The platform may still link users to Bundesagentur search pages as external apply/source destinations.

### Option 4: Use Official Open Statistics as Listings

Pros:

- legal and no-cost
- much larger and more authoritative than local CSV files
- good for market context

Cons:

- not individual job postings
- no company-level application URL
- no full job description
- no direct apply handoff

Decision: use for market context, not for search result listings.

### Option 5: Licensed Provider or Company Career Feeds

Pros:

- production-safe when terms allow the intended use
- can provide real listings and apply URLs
- can scale the product beyond seed data

Cons:

- provider review is required
- may cost money
- coverage and field quality vary
- can create vendor coupling

Decision: future approved path. The provider adapter interface exists so this can be added without changing the search engine.

## Why This Decision Is Still Correct

The platform needs to be engineered honestly. A large but legally unclear dataset would make the UI look better for a short time, but it would weaken the project.

Local legal seed listings let us build the right backend:

- provider contracts
- Pydantic API schemas
- source governance
- search service layer
- apply handoff
- validation
- test coverage

Official open statistics can then make the product smarter without pretending to be job listings.

Approved provider or company-feed listings can be added later through the provider adapter boundary.

## How This Should Be Presented

The project should not say:

- "live German jobs" unless a live approved provider is configured
- "complete German job market" while using seed data
- "official Bundesagentur listings API" unless official terms are confirmed

The project can say:

- local legal seed listings power the current search workflow
- official open datasets can enrich market context
- source governance blocks unapproved ingestion
- production listings require a licensed provider, official API with clear terms, or company feeds with explicit permission

## Tradeoffs Accepted

By using local legal seed listings for now, we accept:

- limited result volume
- illustrative salary and demand insights
- no claim of live coverage
- need for a larger approved listing source later

These tradeoffs are acceptable because the current priority is to engineer a credible backend before rebuilding the frontend.

## Consequences

Positive consequences:

- safer legal posture
- deterministic tests
- reliable local development
- clear separation between listings and market context
- easier future provider integration
- no false claims about live data

Negative consequences:

- the frontend will not feel fully populated until more approved data is added
- market insights from seed listings alone are not statistically meaningful
- extra work is needed to integrate official aggregate datasets

## Next Data Work

Recommended next steps:

1. Expand the local legal seed listing set to 100-300 records across German professions.
2. Add fields needed for real providers:
   - `source_posting_id`
   - `application_url`
   - `company_career_url`
   - `city`
   - `federal_state`
   - `occupation_group`
   - `esco_occupation_uri`
   - `experience_level`
   - `salary_period`
   - `salary_is_estimated`
   - `salary_confidence`
   - `posted_at`
   - `expires_at`
   - `last_seen_at`
   - `ingestion_batch_id`
3. Add ESCO enrichment for occupations and skills.
4. Add Eurostat or BA statistics adapters for market context.
5. Add a live listing provider only after source terms are confirmed.

## Relationship to ADR 009

This ADR explains why the project still uses local legal seed listings for the job-listing layer.

[ADR 009](009-legal-data-and-source-strategy.md) explains the broader legal data strategy:

- what free/legal larger sources exist
- which sources are appropriate for market context
- why unapproved scraping is blocked
- when a live listing provider can be accepted
