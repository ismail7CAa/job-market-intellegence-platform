# Database Migrations

Alembic controls database schema changes for the backend.

Common commands:

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "describe change"
```

The default URL comes from `DATABASE_URL` in `.env` through `config.settings`.
For one-off runs, override it directly:

```bash
alembic -x database_url=sqlite:///data/job_market.db upgrade head
```
