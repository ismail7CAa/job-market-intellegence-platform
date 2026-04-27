"""Tests for experiment tracking and role prediction workflow."""

from pathlib import Path

import pandas as pd
import pytest

from config.settings import get_settings
from src.prediction.role_predictor import RolePredictor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_DATA = PROJECT_ROOT / "data" / "job_postings_training.csv"
EVAL_DATA = PROJECT_ROOT / "data" / "job_postings_production.csv"


class TestRolePredictor:
    """Test suite for RolePredictor."""

    def test_parse_skill_list_feature_engineering(self):
        """Test skill parsing handles CSV strings, lists, and missing values."""
        assert RolePredictor._parse_skill_list("Python; SQL ; ;Docker") == [
            "Python",
            "SQL",
            "Docker",
        ]
        assert RolePredictor._parse_skill_list(["Python", "  FastAPI  ", None]) == [
            "Python",
            "FastAPI",
        ]
        assert RolePredictor._parse_skill_list(None) == []

    def test_prepare_training_frame_feature_defaults(self):
        """Test feature engineering fills optional columns with stable defaults."""
        predictor = RolePredictor()
        raw = pd.DataFrame(
            [
                {
                    "title": "Data Engineer",
                    "description": "Build Python pipelines",
                    "required_skills": "Python;SQL",
                    "salary_min": 100000,
                    "salary_max": 140000,
                    "role_type": "data_engineering",
                }
            ]
        )

        frame = predictor.prepare_training_frame(raw)

        assert frame.loc[0, "skill_count"] == 2
        assert frame.loc[0, "salary_avg"] == 120000
        assert frame.loc[0, "source"] == "unknown"
        assert frame.loc[0, "remote_status"] == "unknown"
        assert frame.loc[0, "location"] == "unknown"
        assert frame.loc[0, "combined_text"] == "Data Engineer Build Python pipelines Python SQL"

    def test_prepare_training_frame(self):
        """Test feature preparation from raw CSV data."""
        predictor = RolePredictor()
        frame = predictor.prepare_training_frame(pd.read_csv(TRAIN_DATA))

        assert "combined_text" in frame.columns
        assert "salary_avg" in frame.columns
        assert "skill_count" in frame.columns
        assert frame["salary_avg"].notna().all()

    def test_train_and_evaluate(self):
        """Test local model performance does not regress below baseline."""
        settings = get_settings()
        predictor = RolePredictor()
        train_frame = pd.read_csv(TRAIN_DATA)
        eval_frame = pd.read_csv(EVAL_DATA)

        predictor.train(train_frame.to_dict(orient="records"))
        metrics, predictions = predictor.evaluate(eval_frame)

        assert predictor.model is not None
        assert "accuracy" in metrics
        assert metrics["accuracy"] >= settings.role_predictor_baseline_accuracy
        assert metrics["f1_macro"] >= settings.role_predictor_baseline_f1_macro
        assert "predicted_role_type" in predictions.columns
        assert len(predictions) == len(eval_frame)

    def test_forecast_role_demand(self):
        """Test role demand forecasting output shape."""
        predictor = RolePredictor()
        train_frame = pd.read_csv(TRAIN_DATA)
        eval_frame = pd.read_csv(EVAL_DATA)

        predictor.train(train_frame.to_dict(orient="records"))
        forecast = predictor.forecast_role_demand(
            eval_frame.to_dict(orient="records"),
            quarters_ahead=2,
            top_n=5,
        )

        assert forecast
        assert all("role" in item for item in forecast)
        assert all("confidence_score" in item for item in forecast)
        assert all(item["quarters_ahead"] == 2 for item in forecast)

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
        assert result["metrics"]["accuracy"] >= 0.8
        assert result["metrics"]["f1_macro"] >= 0.8
        assert result["registered_model_name"] == "test_role_predictor"
