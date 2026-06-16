"""Silver layer: normalize + enrich bronze FIX events and deduplicate.

Pure-function transform. Adds analytic columns the gold features and detectors rely on
(event_kind, asset_class, desk, is_buy, notional) and removes exact duplicate events.
The watermarked order<->execution join is added when this lifts into streaming DLT; the
batch enrichment here is sufficient for the gold aggregates.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def to_silver(bronze: DataFrame) -> DataFrame:
    event_kind = (
        F.when(F.col("msg_type") == "D", F.lit("NEW"))
        .when(F.col("msg_type") == "8", F.lit("EXEC"))
        .when(F.col("msg_type") == "F", F.lit("CANCEL"))
        .when(F.col("msg_type") == "G", F.lit("REPLACE"))
        .otherwise(F.lit("OTHER"))
    )
    df = (
        bronze.withColumn("event_kind", event_kind)
        # equities-only universe for now; map to derivatives by symbol later
        .withColumn("asset_class", F.lit("equity"))
        .withColumn("desk", F.lit("equity"))
        .withColumn("is_buy", F.col("side") == "1")
        .withColumn(
            "notional",
            F.coalesce(F.col("order_qty") * F.col("price"), F.lit(0.0)),
        )
    )
    # drop exact duplicate events (idempotent re-delivery from the bus)
    return df.dropDuplicates(["cl_ord_id", "msg_type", "transact_time", "exec_id"])
