"""Machine learning models for predicting future job market trends."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from config.settings import MLFLOW_REGISTERED_MODEL_NAME
from src.experiments import MLflowExperimentTracker

logger = logging.getLogger(__name__)


class RolePredictor:
    """Predict which roles will spike in demand next quarter."""

    def __init__(self, random_state: int = 42):
        """Initialize the role prediction model."""
        self.model = None
        self.random_state = random_state
        self.label_column = "role_type"
        self.feature_columns = [
            "combined_text",
            "source",
            "remote_status",
            "salary_avg",
            "skill_count",
        ]

    @staticmethod
    def _column_or_default(frame: pd.DataFrame, column_name: str, default_value) -> pd.Series:
        """Return a DataFrame column or a default-filled series."""
        if column_name in frame.columns:
            return frame[column_name]
        return pd.Series([default_value] * len(frame), index=frame.index)

    @staticmethod
    def _combine_text_columns(frame: pd.DataFrame) -> pd.Series:
        """Convert text columns into a single text feature."""
        return frame["combined_text"].fillna("")

    @staticmethod
    def _parse_skill_list(raw_skills: Union[str, Sequence[str], None]) -> List[str]:
        """Normalize skill data from CSV strings or Python lists."""
        if raw_skills is None:
            return []
        if isinstance(raw_skills, str):
            return [skill.strip() for skill in raw_skills.split(";") if skill.strip()]
        return [str(skill).strip() for skill in raw_skills if str(skill).strip()]

    def prepare_training_frame(
        self,
        data: Union[pd.DataFrame, List[Dict]],
        require_label: bool = True,
    ) -> pd.DataFrame:
        """Transform raw job posting data into model features."""
        frame = pd.DataFrame(data).copy() if not isinstance(data, pd.DataFrame) else data.copy()

        if frame.empty:
            raise ValueError("Training data is empty.")
        if require_label and self.label_column not in frame.columns:
            raise ValueError(f"Training data must include '{self.label_column}'.")

        frame["required_skills"] = self._column_or_default(frame, "required_skills", "").apply(
            self._parse_skill_list
        )
        frame["skill_count"] = frame["required_skills"].apply(len)
        frame["salary_min"] = pd.to_numeric(
            self._column_or_default(frame, "salary_min", None),
            errors="coerce",
        )
        frame["salary_max"] = pd.to_numeric(
            self._column_or_default(frame, "salary_max", None),
            errors="coerce",
        )
        frame["salary_avg"] = frame[["salary_min", "salary_max"]].mean(axis=1)
        frame["source"] = self._column_or_default(frame, "source", "unknown").fillna("unknown").astype(str)
        frame["remote_status"] = self._column_or_default(
            frame,
            "remote_status",
            "unknown",
        ).fillna("unknown").astype(str)
        frame["title"] = self._column_or_default(frame, "title", "").fillna("").astype(str)
        frame["description"] = self._column_or_default(frame, "description", "").fillna("").astype(str)
        frame["combined_text"] = (
            frame["title"]
            + " "
            + frame["description"]
            + " "
            + frame["required_skills"].apply(lambda skills: " ".join(skills))
        ).str.strip()

        return frame

    def _build_pipeline(self) -> Pipeline:
        """Build the feature and model pipeline."""
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "text",
                    Pipeline(
                        steps=[
                            (
                                "selector",
                                FunctionTransformer(self._combine_text_columns, validate=False),
                            ),
                            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
                        ]
                    ),
                    ["combined_text"],
                ),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore"),
                    ["source", "remote_status"],
                ),
                (
                    "numeric",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    ["salary_avg", "skill_count"],
                ),
            ]
        )

        return Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                (
                    "classifier",
                    LogisticRegression(max_iter=1000, random_state=self.random_state),
                ),
            ]
        )

    @staticmethod
    def _dataset_signature(data_path: Union[str, Path]) -> str:
        """Create a stable hash for a dataset file."""
        data_path = Path(data_path)
        return hashlib.sha256(data_path.read_bytes()).hexdigest()

    @staticmethod
    def _dataset_profile(frame: pd.DataFrame) -> Dict:
        """Build lightweight dataset metadata for tracking."""
        salary_summary = frame["salary_avg"].describe().fillna(0).to_dict()
        return {
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "label_distribution": {
                str(key): int(value)
                for key, value in frame["role_type"].value_counts().to_dict().items()
            },
            "remote_status_distribution": {
                str(key): int(value)
                for key, value in frame["remote_status"].value_counts().to_dict().items()
            },
            "source_distribution": {
                str(key): int(value)
                for key, value in frame["source"].value_counts().to_dict().items()
            },
            "salary_avg_summary": {
                str(key): float(value)
                for key, value in salary_summary.items()
            },
        }

    def train(self, historical_data: List[Dict]) -> None:
        """Train prediction model on historical data."""
        logger.info(f"Training role predictor with {len(historical_data)} records")
        prepared = self.prepare_training_frame(historical_data)
        model = self._build_pipeline()
        model.fit(prepared[self.feature_columns], prepared[self.label_column])
        self.model = model

    def predict(self, records: Union[pd.DataFrame, List[Dict]]) -> List[Dict]:
        """Predict role labels for new job posting records."""
        if self.model is None:
            raise ValueError("Model has not been trained yet.")

        prepared = self.prepare_training_frame(records, require_label=False)
        predictions = self.model.predict(prepared[self.feature_columns])
        return [
            {"predicted_role_type": prediction}
            for prediction in predictions
        ]

    def evaluate(self, evaluation_data: Union[pd.DataFrame, List[Dict]]) -> Tuple[Dict[str, float], pd.DataFrame]:
        """Evaluate the trained model on a labeled dataset."""
        if self.model is None:
            raise ValueError("Model has not been trained yet.")

        prepared = self.prepare_training_frame(evaluation_data)
        features = prepared[self.feature_columns]
        truth = prepared[self.label_column]
        predictions = self.model.predict(features)

        report = classification_report(truth, predictions, output_dict=True, zero_division=0)
        metrics = {
            "accuracy": accuracy_score(truth, predictions),
            "f1_macro": f1_score(truth, predictions, average="macro", zero_division=0),
            "f1_weighted": f1_score(truth, predictions, average="weighted", zero_division=0),
        }
        metrics.update(
            {
                "precision_macro": report["macro avg"]["precision"],
                "recall_macro": report["macro avg"]["recall"],
            }
        )

        predictions_frame = prepared.copy()
        predictions_frame["predicted_role_type"] = predictions
        return metrics, predictions_frame

    def run_experiment(
        self,
        training_data_path: Union[str, Path],
        evaluation_data_path: Union[str, Path],
        tracking_uri: Optional[str] = None,
        experiment_name: Optional[str] = None,
        artifact_root: Optional[str] = None,
        registered_model_name: Optional[str] = None,
        run_name: Optional[str] = None,
        register_model: bool = True,
    ) -> Dict:
        """Train and track a role prediction experiment in MLflow."""
        tracker = MLflowExperimentTracker(
            tracking_uri=tracking_uri,
            experiment_name=experiment_name,
            artifact_root=artifact_root,
        )
        experiment_id = tracker.configure()

        try:
            import mlflow
            import mlflow.sklearn
            from mlflow.models import infer_signature
            from mlflow.tracking import MlflowClient
        except ImportError as exc:
            raise ImportError(
                "MLflow is required for experiment tracking. "
                "Install project dependencies or run `pip install mlflow`."
            ) from exc

        training_data_path = Path(training_data_path)
        evaluation_data_path = Path(evaluation_data_path)
        train_frame = self.prepare_training_frame(pd.read_csv(training_data_path))
        eval_frame = self.prepare_training_frame(pd.read_csv(evaluation_data_path))

        self.model = self._build_pipeline()
        self.model.fit(train_frame[self.feature_columns], train_frame[self.label_column])

        metrics, predictions_frame = self.evaluate(eval_frame)
        report = classification_report(
            predictions_frame[self.label_column],
            predictions_frame["predicted_role_type"],
            output_dict=True,
            zero_division=0,
        )

        registered_model_name = registered_model_name or MLFLOW_REGISTERED_MODEL_NAME
        run_tags = {
            "model_family": "role_classifier",
            "problem_type": "multiclass_classification",
            "train_dataset_sha256": self._dataset_signature(training_data_path),
            "eval_dataset_sha256": self._dataset_signature(evaluation_data_path),
        }
        run_params = {
            "train_rows": len(train_frame),
            "eval_rows": len(eval_frame),
            "feature_count": len(self.feature_columns),
            "random_state": self.random_state,
            "model_type": "logistic_regression",
            "text_vectorizer": "tfidf_unigram_bigram",
            "registered_model_name": registered_model_name,
        }

        with tempfile.TemporaryDirectory() as artifact_dir:
            artifact_path = Path(artifact_dir)
            predictions_file = artifact_path / "predictions.csv"
            classification_report_file = artifact_path / "classification_report.json"
            dataset_profile_file = artifact_path / "dataset_profile.json"
            confusion_matrix_file = artifact_path / "confusion_matrix.csv"

            predictions_frame.to_csv(predictions_file, index=False)
            classification_report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
            dataset_profile_file.write_text(
                json.dumps(
                    {
                        "train": self._dataset_profile(train_frame),
                        "evaluation": self._dataset_profile(eval_frame),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            pd.crosstab(
                predictions_frame[self.label_column],
                predictions_frame["predicted_role_type"],
                rownames=["actual"],
                colnames=["predicted"],
            ).to_csv(confusion_matrix_file)

            with mlflow.start_run(run_name=run_name or "role-prediction-training") as run:
                mlflow.set_tags(run_tags)
                mlflow.log_params(run_params)
                mlflow.log_metrics(metrics)
                mlflow.log_artifact(str(predictions_file), artifact_path="evaluation")
                mlflow.log_artifact(str(classification_report_file), artifact_path="evaluation")
                mlflow.log_artifact(str(dataset_profile_file), artifact_path="metadata")
                mlflow.log_artifact(str(confusion_matrix_file), artifact_path="evaluation")

                signature = infer_signature(
                    train_frame[self.feature_columns],
                    self.model.predict(train_frame[self.feature_columns]),
                )
                model_info = mlflow.sklearn.log_model(
                    sk_model=self.model,
                    artifact_path="model",
                    signature=signature,
                    input_example=train_frame[self.feature_columns].head(3),
                    registered_model_name=registered_model_name if register_model else None,
                )

            registered_model_version = None
            if register_model:
                client = MlflowClient(tracking_uri=tracker.tracking_uri, registry_uri=tracker.tracking_uri)
                for version in client.search_model_versions(f"name='{registered_model_name}'"):
                    if version.run_id == run.info.run_id:
                        registered_model_version = version.version
                        break

        return {
            "experiment_id": experiment_id,
            "run_id": run.info.run_id,
            "run_name": run.data.tags.get("mlflow.runName"),
            "tracking_uri": tracker.tracking_uri,
            "artifact_root": tracker.artifact_root,
            "metrics": metrics,
            "registered_model_name": registered_model_name if register_model else None,
            "registered_model_version": registered_model_version,
            "model_uri": model_info.model_uri,
        }

    def predict_next_quarter(self) -> List[Dict]:
        """Predict top in-demand roles for the next quarter."""
        logger.info("Predicting demand for next quarter")
        if self.model is None:
            logger.warning("Role predictor has not been trained yet")
            return []
        return [
            {
                "message": "Demand forecasting requires time-series trend features. "
                "The current experiment tracker now supports training and registry for role classification."
            }
        ]
