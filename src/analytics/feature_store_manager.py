"""Feature store manager for Feast integration."""

import logging
from datetime import datetime
from feast import FeatureStore
from feast.data_source import BigQuerySource
from feast.entity import Entity
from feast.feature_view import FeatureView
from feast.field import Field
from feast.types import Float32, Int64, String
from feast.value_type import ValueType

logger = logging.getLogger(__name__)

class FeatureStoreManager:
    """Manages Feast feature store operations."""

    def __init__(self, repo_path: str = "/app/feast"):
        self.store = FeatureStore(repo_path=repo_path)

    def apply_feature_definitions(self):
        """Apply feature definitions to the store."""
        # This would be done via feast apply command, but for programmatic:
        # Define entities and feature views in features.py and run feast apply
        pass

    def materialize_features(self, start_date: str, end_date: str):
        """Materialize features to online store."""
        from feast.cli import apply_total

        # Apply feature definitions
        apply_total(self.store.config)

        # Materialize
        self.store.materialize(start_date=start_date, end_date=end_date)

    def get_online_features(self, entity_rows: list, features: list):
        """Retrieve online features."""
        return self.store.get_online_features(
            entity_rows=entity_rows,
            features=features
        ).to_df()

    def get_historical_features(self, entity_df, features: list):
        """Retrieve historical features."""
        return self.store.get_historical_features(
            entity_df=entity_df,
            features=features
        ).to_df()