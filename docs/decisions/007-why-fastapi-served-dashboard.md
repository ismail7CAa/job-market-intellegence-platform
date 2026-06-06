# ADR 007: Why Serve the Job Search Frontend from FastAPI

- Status: Accepted
- Date: 2026-05-19
- Updated: 2026-06-06

## Context

After the backend moved from a generic analytics dashboard toward a German job-search and apply platform, the frontend also needed to change. The public URL should no longer feel like a technical demo or an AI-agent experiment. It should feel like a serious job-market intelligence product:

- search jobs across German sectors
- filter and inspect results
- understand salary context
- see why a job matched
- open an approved apply or company/source URL

The project could add a separate frontend application, but the current deployment is intentionally simple: one EC2 instance, one FastAPI app container, and one Postgres container.

## Decision

Serve a static HTML/CSS/JavaScript frontend from FastAPI.

The frontend lives under:

```text
job-intelligence/
├── index.html
├── results.html
├── css/
│   ├── base.css
│   ├── search.css
│   └── results.css
└── js/
    ├── api.js
    ├── search.js
    └── results.js
```

FastAPI serves:

- `/` as the search landing page
- `/results` as the results dashboard
- `/job-intelligence/...` as static CSS and JavaScript assets

The frontend uses plain HTML, CSS, and vanilla JavaScript. Python/FastAPI remains the server and API layer.

## Options Considered

### Option 1: FastAPI-Served Static HTML/CSS/JavaScript

Pros:

- no extra deployment layer
- same EC2 container serves API and frontend
- no Node, npm, Vite, or build pipeline required
- easy to call the existing FastAPI endpoints directly
- frontend files are separate from Python route code
- avoids adding Node/Vite build steps before the first live portfolio version is stable
- enough structure for the current product workflow: search, filter, inspect, apply

Cons:

- less component structure than React
- richer future state management would require refactoring
- no frontend bundler, minification, or typed client generation yet

### Option 2: React or Vite Frontend

Pros:

- stronger modern frontend architecture
- better component structure
- more room for interactive charts and richer state management

Cons:

- requires another build pipeline
- introduces static asset hosting or reverse proxy decisions
- more moving parts during early deployment
- increases complexity before the backend/frontend product contract has been tested by users

### Option 3: Python-Only Templates

Pros:

- keeps all rendering inside Python
- can reuse backend data directly
- avoids JavaScript for basic pages

Cons:

- tends to mix UI markup with backend route code
- harder to build a responsive, app-like search/result workflow cleanly
- less natural for client-side filters, selection state, pagination, and detail panels

### Option 4: Streamlit Dashboard

Pros:

- very fast for data science dashboards
- good for charts and exploratory analysis
- familiar to many DS/ML reviewers

Cons:

- another service to deploy
- less polished as a product web app
- weaker fit with the existing FastAPI API surface
- does not match the product direction of a job search/apply experience

## Why FastAPI-Served Static Frontend Was Chosen

The project is currently proving end-to-end delivery. The most valuable next step was to make the deployed URL feel like a product without destabilizing the deployment architecture.

Serving static frontend files from FastAPI keeps the first public version simple and still demonstrates:

- backend API engineering
- frontend product thinking
- search and apply workflow design
- API contract usage
- cloud deployment

The programming-language split is intentional:

- Python remains responsible for API, repository access, ingestion, validation, governance, salary estimation, and deployment config.
- HTML defines document structure for the search and result pages.
- CSS owns the editorial dark intelligence visual system.
- JavaScript owns browser-side state: URL params, API calls, filter rendering, result rendering, detail panel selection, pagination, and error display.

This is a better fit than Python-only rendering because the results page is interactive, but it avoids the cost of a full frontend framework before it is necessary.

## Tradeoffs Accepted

By keeping the frontend static and FastAPI-served for now, we accept:

- less frontend modularity than a component framework
- manual DOM rendering in JavaScript
- future refactoring if the UI grows into a full application

Those tradeoffs are acceptable for the current portfolio stage. A React frontend can still become a future ADR once the app needs deeper interaction and a separate asset pipeline.

## Consequences

Positive consequences:

- the public URL opens a real search experience
- reviewers can inspect product behavior without opening Swagger first
- the UI calls the same Pydantic-backed API contracts that external clients use
- frontend code is no longer embedded in `src/api/main.py`
- deployment remains one app container plus Postgres

Negative consequences:

- frontend code is not organized as framework components
- adding sophisticated charts, saved searches, authentication, or account workflows may require a dedicated frontend stack
- static assets should be checked manually in a browser after visual changes
