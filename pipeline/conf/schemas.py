"""PySpark StructType MIRROR of the canonical Alert contract.

Mirror of pipeline/shared/models/alert_contract.py (the master). Kept in lockstep by
tests/contract/. Field names, order, and nullability must match the Pydantic model.
"""

from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

FEATURE_CONTRIBUTION = StructType(
    [
        StructField("feature_name", StringType(), False),
        StructField("feature_value", DoubleType(), False),
        StructField("shap_value", DoubleType(), False),
        StructField("rank", IntegerType(), False),
        StructField("direction", StringType(), False),
    ]
)

ALERT_SCHEMA = StructType(
    [
        StructField("alert_id", StringType(), False),
        StructField("detector", StringType(), False),
        StructField("trader_id", StringType(), False),  # PII
        StructField("instrument", StringType(), False),
        StructField("window_start", LongType(), False),  # epoch millis
        StructField("window_end", LongType(), False),
        StructField("severity", IntegerType(), False),  # 1..5
        StructField("rule_score", DoubleType(), False),  # 0..1, authoritative
        StructField("ml_score", DoubleType(), True),  # nullable until ML fills it
        StructField("shap_top_features", ArrayType(FEATURE_CONTRIBUTION), False),
        StructField("triggering_event_ids", ArrayType(StringType()), False),
        StructField("regulation_refs", ArrayType(StringType()), False),
        StructField("desk", StringType(), False),
        StructField("created_at", LongType(), False),
        StructField("audit_hash", StringType(), False),
    ]
)

CATALOG = "sentinel_trace"
SCHEMAS = ("bronze", "silver", "gold", "alerts", "governed_output", "eval", "ml")
