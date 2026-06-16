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

# Bronze raw FIX event schema (all nullable; schema enforcement happens via the
# REQUIRED_BRONZE_FIELDS not-null filter, not via column nullability). Field names mirror
# generator/synthfix/fix.py FixEvent so generator dicts map straight in.
RAW_FIX_SCHEMA = StructType(
    [
        StructField("msg_type", StringType(), True),
        StructField("cl_ord_id", StringType(), True),
        StructField("trader_id", StringType(), True),
        StructField("account", StringType(), True),
        StructField("symbol", StringType(), True),
        StructField("side", StringType(), True),
        StructField("order_qty", LongType(), True),
        StructField("ord_type", StringType(), True),
        StructField("transact_time", LongType(), True),
        StructField("exchange_id", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("exec_type", StringType(), True),
        StructField("order_id", StringType(), True),
        StructField("exec_id", StringType(), True),
        StructField("last_qty", LongType(), True),
        StructField("last_px", DoubleType(), True),
        StructField("orig_cl_ord_id", StringType(), True),
        StructField("cancel_reason", StringType(), True),
        StructField("scenario_id", StringType(), True),
        StructField("scenario_type", StringType(), True),
    ]
)

# Every well-formed FIX event must carry these (regardless of msg type).
REQUIRED_BRONZE_FIELDS = [
    "msg_type", "cl_ord_id", "trader_id", "account", "symbol",
    "side", "order_qty", "ord_type", "transact_time", "exchange_id",
]
