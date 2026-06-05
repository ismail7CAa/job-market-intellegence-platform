# ADR 006: Why Focus the Portfolio Demo on the German Job Market

- Status: Accepted
- Date: 2026-05-16

## Context

The project originally had a broad job-market intelligence theme. A broad market can be useful eventually, but it makes the portfolio story less specific. The public demo benefits from a clearer market, currency, location set, and audience.

Germany is a strong focus for this version because the product can center on:

- German jobs across professions
- German cities
- EUR salaries
- regional demand and salary context
- a market context relevant to the user's job-search goals

## Decision

Focus the public portfolio version on the German job market.

This affects:

- sample data
- default keywords
- salary currency
- API title and description
- landing-page copy
- documentation narrative

## Options Considered

### Option 1: German Market Focus

Pros:

- stronger product narrative
- consistent salary currency and location context
- easier for reviewers to understand the scope
- aligns with a realistic regional analytics product

Cons:

- narrower market coverage
- future data sourcing should be Germany-specific
- role and salary interpretation should not be generalized globally

### Option 2: Generic Global Market

Pros:

- broader positioning
- easier to reuse mixed-source datasets
- avoids committing to one region too early

Cons:

- weaker demo story
- salaries and job markets become harder to compare
- data can look inconsistent when cities, currencies, and roles are mixed

### Option 3: US Market Focus

Pros:

- many public examples and datasets exist
- larger English-language tech-job dataset ecosystem

Cons:

- less aligned with the intended portfolio positioning
- keeps USD assumptions in a project that now wants a German-market identity

## Why Germany Was Chosen

Germany gives the product a concrete audience and makes the demo easier to understand.

Instead of presenting a vague global analytics platform, the project now says:

> This is a job-search and market-intelligence platform for jobs in Germany.

That specificity makes the data, API responses, and deployment page feel more intentional while still allowing roles outside tech.

## Tradeoffs Accepted

By focusing on Germany, we accept:

- narrower scope
- need for Germany-specific source strategy later
- care around language, salary bands, and regional interpretation

Those tradeoffs are acceptable because the portfolio version benefits from clarity more than breadth.

## Consequences

Positive consequences:

- clearer demo positioning
- EUR salary consistency
- better first impression on the deployed homepage
- easier future roadmap toward German data providers or datasets

Negative consequences:

- global claims should be avoided
- live-data expansion needs market-specific sourcing
