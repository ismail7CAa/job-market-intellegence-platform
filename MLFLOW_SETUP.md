# MLflow Experiment Tracking

This project tracks role prediction experiments with MLflow using the local training and production datasets:

- `data/job_postings_training.csv`
- `data/job_postings_production.csv`

## What gets tracked

- Versioned runs keyed by dataset SHA-256 fingerprints
- Params describing the model and feature setup
- Metrics including accuracy, macro F1, macro precision, and macro recall
- Artifacts:
  - `evaluation/predictions.csv`
  - `evaluation/classification_report.json`
  - `evaluation/confusion_matrix.csv`
  - `metadata/dataset_profile.json`
- Registered model versions in the MLflow model registry

## Run an experiment

```bash
python cli.py track-experiment \
  --train-data data/job_postings_training.csv \
  --eval-data data/job_postings_production.csv
```

Optional overrides:

```bash
python cli.py track-experiment \
  --experiment-name role-prediction-dev \
  --run-name baseline-logreg \
  --tracking-uri sqlite:///mlflow.db \
  --artifact-root file:///absolute/path/to/mlartifacts \
  --registered-model-name job_market_role_predictor
```

If you want to skip model registration for a run:

```bash
python cli.py track-experiment --skip-registry
```

## Open the MLflow UI

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Then open `http://127.0.0.1:5000`.

## Environment variables

You can override the defaults with:

- `MLFLOW_TRACKING_URI`
- `MLFLOW_ARTIFACT_ROOT`
- `MLFLOW_EXPERIMENT_NAME`
- `MLFLOW_REGISTERED_MODEL_NAME`
