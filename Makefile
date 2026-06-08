.PHONY: help install ingest train serve test docker-check migrate migration

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
UVICORN ?= uvicorn

LIMIT ?= 100
OUTPUT ?= data/jobs.csv
FETCH_ARGS ?=
HOST ?= 0.0.0.0
PORT ?= 8000
TRAIN_DATA ?= data/job_postings_training.csv
EVAL_DATA ?= data/job_postings_production.csv
PYTEST_ARGS ?= tests

help:
	@echo "Available targets:"
	@echo "  make install    Install Python dependencies"
	@echo "  make ingest     Run the ingestion pipeline"
	@echo "  make train      Retrain and track the role predictor"
	@echo "  make serve      Start the FastAPI app"
	@echo "  make test       Run the test suite"
	@echo "  make docker-check  Verify the Dockerized app, frontend, and search API"
	@echo "  make migrate    Apply Alembic migrations"
	@echo "  make migration MESSAGE='describe change'  Create an Alembic revision"
	@echo ""
	@echo "Common overrides:"
	@echo "  make ingest LIMIT=25 OUTPUT=data/jobs.json"
	@echo "  make ingest FETCH_ARGS='--source linkedin --keyword \"Data Engineer\"'"
	@echo "  make train TRAIN_DATA=data/job_postings_training.csv EVAL_DATA=data/job_postings_production.csv"
	@echo "  make serve HOST=127.0.0.1 PORT=8000"
	@echo "  make test PYTEST_ARGS='tests/test_data_pipeline.py -q'"

install:
	$(PIP) install -r requirements.txt

ingest:
	$(PYTHON) cli.py fetch --limit $(LIMIT) --output $(OUTPUT) $(FETCH_ARGS)

train:
	$(PYTHON) cli.py track-experiment --train-data $(TRAIN_DATA) --eval-data $(EVAL_DATA) --skip-registry

serve:
	$(UVICORN) src.api.main:app --host $(HOST) --port $(PORT) --reload

test:
	$(PYTHON) -m pytest $(PYTEST_ARGS)

docker-check:
	bash scripts/check-docker-app.sh

migrate:
	$(PYTHON) -m alembic upgrade head

migration:
	$(PYTHON) -m alembic revision --autogenerate -m "$(MESSAGE)"
