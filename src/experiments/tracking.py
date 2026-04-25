"""Helpers for configuring MLflow experiments and model registry."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from config.settings import (
    MLFLOW_ARTIFACT_ROOT,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
)


class MLflowExperimentTracker:
    """Configure and manage MLflow experiment metadata."""

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: Optional[str] = None,
        artifact_root: Optional[str] = None,
    ):
        self.tracking_uri = tracking_uri or MLFLOW_TRACKING_URI
        self.experiment_name = experiment_name or MLFLOW_EXPERIMENT_NAME
        self.artifact_root = artifact_root or MLFLOW_ARTIFACT_ROOT

    def _import_mlflow(self):
        try:
            import mlflow
        except ImportError as exc:
            raise ImportError(
                "MLflow is required for experiment tracking. "
                "Install project dependencies or run `pip install mlflow`."
            ) from exc
        return mlflow

    def _ensure_tracking_store(self) -> None:
        if self.tracking_uri.startswith("sqlite:///"):
            database_path = Path(self.tracking_uri.replace("sqlite:///", "", 1))
            database_path.parent.mkdir(parents=True, exist_ok=True)

        if self.artifact_root.startswith("file://"):
            parsed = urlparse(self.artifact_root)
            artifact_path = Path(unquote(parsed.path))
            if parsed.netloc and parsed.netloc not in {"", "localhost"}:
                artifact_path = Path(f"/{parsed.netloc}{artifact_path}")

            artifact_path.mkdir(
                parents=True,
                exist_ok=True,
            )

    def configure(self) -> str:
        """Set tracking configuration and ensure the experiment exists."""
        mlflow = self._import_mlflow()
        self._ensure_tracking_store()

        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.tracking_uri)

        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(
                name=self.experiment_name,
                artifact_location=self.artifact_root,
            )
        else:
            experiment_id = experiment.experiment_id

        mlflow.set_experiment(self.experiment_name)
        return experiment_id
