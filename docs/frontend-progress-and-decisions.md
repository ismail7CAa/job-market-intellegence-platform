# Frontend Progress and Problem-Solution Log

This document records the first frontend implementation step for the German Job Market Intelligence Platform.

## Product Goal

The frontend should make the core workflow simple:

1. Search for a job in Germany.
2. Review matching jobs with company, location, salary, and match reasons.
3. Filter and sort the result set.
4. Inspect a selected job in detail.
5. Open the approved source or company application page.

The UI should feel like an editorial dark intelligence product: serious, fast, data-focused, and trustworthy.

## 1. The Old Frontend Was Too Dashboard-Like

Problem:

- The earlier FastAPI root page was an embedded dashboard inside Python.
- It was not focused enough on the new job-search/apply product.
- Frontend markup and styling inside `src/api/main.py` would become hard to maintain.

Solution:

- Added a dedicated static frontend under `job-intelligence/`.
- Replaced the root route with `index.html`.
- Added `/results` for the search results dashboard.
- Mounted `/job-intelligence/...` for CSS and JavaScript assets.

Why:

- The frontend becomes easier to edit without touching backend route code.
- The deployment stays simple because FastAPI still serves the frontend.
- The UI can now evolve as a product surface instead of a generated Python string.

## 2. We Chose HTML, CSS, JavaScript, and Python Together

Problem:

- A Python-only UI would keep everything in the backend but would make interactive search state awkward.
- A React/Vite frontend would be powerful but adds a build pipeline before the first frontend slice is validated.

Solution:

- Use Python/FastAPI for the API and static file serving.
- Use HTML for page structure.
- Use CSS for the visual system.
- Use vanilla JavaScript for URL params, API calls, filters, pagination, result rendering, detail panels, and error display.

Why:

- This keeps the one-container deployment model.
- It gives enough interactivity for the current workflow.
- It avoids Node/npm/Vite complexity until the product needs a larger frontend architecture.

## 3. Search Page

Implemented:

- `job-intelligence/index.html`
- `job-intelligence/css/base.css`
- `job-intelligence/css/search.css`
- `job-intelligence/js/search.js`

The search page provides:

- brand identity
- one simple inspiring platform sentence instead of explanatory marketing blocks
- job/profession search input
- location input
- quick searches such as `Pflege`, `Buchhaltung`, `Logistik`, `Sales Manager`, and `Data Analyst`
- direct navigation to `/results` after storing the backend search payload in `sessionStorage`

## 4. Results Dashboard

Implemented:

- `job-intelligence/results.html`
- `job-intelligence/css/results.css`
- `job-intelligence/js/api.js`
- `job-intelligence/js/results.js`

The results dashboard provides:

- top search bar
- filter rail for sorting, company, role type, employment type, and salary range
- search intelligence summary
- job result list with salary type, relevance, tags, and match reasons
- selected job detail panel
- salary, market context, skills, source policy, similar jobs, and apply handoff
- standard error display using the backend error contract

## 5. API Integration Without Showing Raw JSON

Problem:

- Users should never be sent to a raw JSON API response.
- The browser URL should not be the source of truth for result rendering.
- The results page should render product UI from backend data, not expose backend payloads directly.

Solution:

- `search.js` calls the backend search API on submit.
- The returned `JobSearchResponse` is stored in `sessionStorage`.
- The browser then navigates to `/results`.
- `results.js` reads the stored payload from `sessionStorage`.
- If no stored payload exists, `/results` redirects back to `/`.
- Filter, sort, and pagination changes refresh the backend payload and replace the stored result.

Why:

- The user always sees cards, filters, summaries, and detail panels instead of raw JSON.
- The backend API remains clean and reusable.
- The frontend keeps the first result render fast because the first payload is already available when `/results` opens.

## 6. Design Direction

Chosen style:

- editorial dark intelligence
- deep charcoal/navy backgrounds
- warm amber/gold accents
- serif display headings
- geometric/system sans UI text
- sharp, dense, analyst-style layout

Rejected:

- bubbly SaaS styling
- heavy gradients
- decorative cards that do not support the workflow
- extra landing-page status columns that repeat backend concepts instead of helping users search
- visible AI-agent surface for this product step

Why:

- The product should feel authoritative and useful for job-market analysis.
- The backend has serious data-governance and salary-context work; the frontend should visually match that credibility.

## 7. Tests Added

Added API endpoint tests that verify:

- `/` serves the maintained static search page
- `/results` serves the maintained static results page

These tests protect the routing contract. Full visual QA still needs a browser pass once the local server is running.

## 8. Polish Pass

Problem:

- The first functional frontend slice worked, but it needed stronger interaction feedback before visual review.
- Searches and filter changes needed a clearer loading state.
- Cards and panels needed sharper affordance so users understand what is clickable or selected.
- Mobile layouts needed safer spacing and hierarchy.

Solution:

- Added focus-visible states for keyboard users.
- Added restrained hover/active feedback for buttons, chips, result cards, apply links, and similar-job rows.
- Added loading classes and skeleton placeholders for search and result refreshes.
- Improved selected-card styling with an amber accent line.
- Added subtle entrance motion while respecting `prefers-reduced-motion`.
- Tightened responsive spacing for the filter rail, result column, and detail panel.

Why:

- The frontend should feel fast and data-serious without becoming flashy.
- The UI now gives clear feedback while preserving the editorial dark intelligence direction.
- The next visual pass can focus on real browser screenshots rather than basic interaction gaps.

## Remaining Frontend Work

Next frontend steps:

1. Run the local server and inspect desktop/mobile screenshots.
2. Tune spacing, type scale, and responsive behavior after visual review.
3. Add stronger empty/loading states after real browser testing.
4. Consider a saved-search or compare mode only after the basic search/apply flow feels excellent.
5. If the frontend grows significantly, revisit React/Vite in a new ADR.
