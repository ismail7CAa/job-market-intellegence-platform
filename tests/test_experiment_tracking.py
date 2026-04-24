"""Tests for experiment tracking and role prediction workflow."""

from pathlib import Path

import pandas as pd
import pytest

from src.prediction.role_predictor import RolePredictor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_DATA = PROJECT_ROOT / "data" / "job_postings_training.csv"
EVAL_DATA = PROJECT_ROOT / "data" / "job_postings_production.csv"


class TestRolePredictor:
    """Test suite for RolePredictor."""

    def test_prepare_training_frame(self):
        """Test feature preparation from raw CSV data."""
        predictor = RolePredictor()
        frame = predictor.prepare_training_frame(pd.read_csv(TRAIN_DATA))

        assert "combined_text" in frame.columns
        assert "salary_avg" in frame.columns
        assert "skill_count" in frame.columns
        assert frame["salary_avg"].notna().all()

    def test_train_and_evaluate(self):
        """Test local model training and evaluation."""
        predictor = RolePredictor()
        train_frame = pd.read_csv(TRAIN_DATA)
        eval_frame = pd.read_csv(EVAL_DATA)

        predictor.train(train_frame.to_dict(orient="records"))
        metrics, predictions = predictor.evaluate(eval_frame)

        assert predictor.model is not None
        assert "accuracy" in metrics
        assert "predicted_role_type" in predictions.columns
        assert len(predictions) == len(eval_frame)

    def test_run_experiment_with_mlflow(self, tmp_path):
        """Test MLflow experiment execution when MLflow is available."""
        pytest.importorskip("mlflow")

        predictor = RolePredictor()
        result = predictor.run_experiment(
            training_data_path=TRAIN_DATA,
            evaluation_data_path=EVAL_DATA,
            tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}",
            artifact_root=(tmp_path / "artifacts").resolve().as_uri(),
            experiment_name="test-role-prediction",
            registered_model_name="test_role_predictor",
            run_name="pytest-run",
            register_model=True,
        )

        assert result["run_id"]
        assert result["experiment_id"]
        assert result["metrics"]["accuracy"] >= 0
        assert result["registered_model_name"] == "test_role_predictor"
