# ADR 007: Why Serve the Portfolio Dashboard from FastAPI

- Status: Accepted
- Date: 2026-05-19

## Context

After the EC2 deployment was working, the project needed a stronger first impression than a plain JSON landing route. A portfolio reviewer should be able to open the public URL and immediately understand the product: German tech labor-market analytics, ML forecasts, salary anomaly detection, and a grounded market agent.

The project could add a separate frontend application, but the current deployment is intentionally simple: one EC2 instance, one FastAPI app container, and one Postgres container.

## Decision

Serve an advanced dashboard directly from the FastAPI root route in `src/api/main.py`.

The dashboard includes:

- market metrics
- top skill demand bars
- role forecast output
- salary anomaly watch table
- German city and work-mode coverage
- an "Ask the Market Agent" input that calls `/query`
- links to `/docs`, `/health`, `/stats/jobs`, and model/analytics endpoints

## Options Considered

### Option 1: FastAPI-Served HTML/CSS/JavaScript

Pros:

- no extra deployment layer
- same EC2 container serves API and dashboard
- fastest path to a polished public demo
- easy to keep dashboard data close to existing endpoints
- avoids adding Node/Vite build steps before the first live portfolio version is stable

Cons:

- less scalable as frontend complexity grows
- larger HTML template inside `src/api/main.py`
- fewer frontend component abstractions

### Option 2: React or Vite Frontend

Pros:

- stronger modern frontend architecture
- better component structure
- more room for interactive charts and richer state management

Cons:

- requires another build pipeline
- introduces static asset hosting or reverse proxy decisions
- more moving parts during early deployment

### Option 3: Streamlit Dashboard

Pros:

- very fast for data science dashboards
- good for charts and exploratory analysis
- familiar to many DS/ML reviewers

Cons:

- another service to deploy
- less polished as a product web app
- weaker fit with the existing FastAPI API surface

## Why FastAPI-Served Dashboard Was Chosen

The project is currently proving end-to-end delivery. The most valuable next step was to make the deployed URL feel like a product without destabilizing the deployment architecture.

Serving the dashboard from FastAPI keeps the first public version simple and still demonstrates:

- backend API engineering
- frontend product thinking
- analytics visualization
- agent surface design
- cloud deployment

## Tradeoffs Accepted

By keeping the dashboard inside FastAPI for now, we accept:

- less frontend modularity
- a larger route implementation
- future refactoring if the UI grows into a full application

Those tradeoffs are acceptable for the current portfolio stage. A React frontend can still become a future ADR once the app needs deeper interaction and a separate asset pipeline.

## Consequences

Positive consequences:

- the public URL now has a strong first impression
- reviewers can inspect product behavior without opening Swagger first
- the AI agent is visible on the surface
- deployment remains one app container plus Postgres

Negative consequences:

- frontend code is not yet organized as components
- adding sophisticated charts later may require a dedicated frontend stack

