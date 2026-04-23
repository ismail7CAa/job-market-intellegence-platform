from feast import Entity, FeatureView, Feature, ValueType, BigQuerySource
from datetime import timedelta

# Define entity
job_skill = Entity(name="job_skill", join_keys=["skill"])

# Define feature view
skill_demand_features = FeatureView(
    name="skill_demand",
    entities=[job_skill],
    ttl=timedelta(days=365),
    features=[
        Feature(name="demand_score", dtype=ValueType.FLOAT),
        Feature(name="avg_salary", dtype=ValueType.FLOAT),
        Feature(name="job_count", dtype=ValueType.INT64),
        Feature(name="growth_rate", dtype=ValueType.FLOAT),
    ],
    online=True,
    input=BigQuerySource(
        table_ref="your-gcp-project-id.job_market_gold.skill_demand_features",
        event_timestamp_column="event_timestamp",
    ),
)