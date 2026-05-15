# ADR 004: Why Demo Data for the Public Portfolio Version

- Status: Accepted
- Date: 2026-05-16

## Context

The platform is designed to analyze job postings, skills, salaries, and role demand. A fully live version would pull fresh job data from external sources. However, public job data collection has practical and compliance constraints:

- job boards often restrict scraping in their terms of service
- official APIs may require approval, paid access, or limited scopes
- datasets can have licensing restrictions
- external schemas change without warning
- credentials must not be exposed in a public repository
- live ingestion can be unreliable during portfolio review

The project still needs to demonstrate a real analytics and ML workflow in a reproducible way.

## Decision

Use a small committed German job-market demo dataset for the public portfolio deployment.

The demo data lives in:

- `data/job_postings_training.csv`
- `data/job_postings_production.csv`

The dataset is intentionally focused on German tech roles, German cities, and EUR salary ranges.

## Options Considered

### Option 1: Demo Dataset Checked into the Repository

Pros:

- reproducible for local tests, GitHub Actions, and EC2 deployment
- does not require external credentials
- avoids job-board scraping compliance risk
- keeps the public demo stable for reviewers
- allows the app to show analytics, predictions, anomalies, and query behavior immediately

Cons:

- not a claim of live market coverage
- smaller than a production dataset
- trends are illustrative rather than statistically representative

### Option 2: Fully Live Scraping

Pros:

- freshest possible data
- stronger real-world signal if done correctly
- better long-term product value

Cons:

- compliance and terms-of-service risk
- unstable deployment behavior
- risk of blocked requests or broken parsers
- requires careful rate limiting and monitoring
- not ideal for a first portfolio demo

### Option 3: Licensed or Public Third-Party Dataset

Pros:

- larger and more realistic than hand-curated demo data
- more suitable for deeper analysis
- can be legally safer if licensing is clear

Cons:

- still requires license review
- may not be Germany-specific
- may be stale or inconsistent
- adds data acquisition work before deployment

## Why Demo Data Was Chosen

Demo data was chosen because the first public deployment needs to be reliable, legal, and easy to reproduce.

The goal of this portfolio version is to demonstrate the engineering system:

- ingestion contracts
- validation
- skill analytics
- salary anomaly detection
- role prediction
- FastAPI serving
- Dockerized deployment
- database initialization

Those capabilities can be demonstrated without pretending to have full live market coverage.

## How This Should Be Presented

The project should be honest about the data:

- it is a German-market demo dataset
- it is used to make the public deployment reproducible
- live ingestion is a future extension
- production-safe data sourcing would require API access, licensing, or a compliant provider

This is stronger than claiming live data before the source, permissions, and monitoring are ready.

## Tradeoffs Accepted

By using demo data, we accept:

- limited sample size
- illustrative rather than definitive trends
- no claim of real-time market coverage

These tradeoffs are acceptable because the portfolio goal is to show system design and implementation quality, not to sell a production labor-market dataset.

## Consequences

Positive consequences:

- reliable public demo
- no external credential requirement
- stable automated tests
- safer legal and ethical posture
- clearer Germany-focused product narrative

Negative consequences:

- future work is needed for real market coverage
- data quality and representativeness are limited by design
- reviewers should understand the dataset is intentionally scoped

