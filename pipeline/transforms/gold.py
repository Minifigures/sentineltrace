"""Gold layer: per-(trader, instrument, time-window) surveillance features.

Pure-function aggregation over silver. These are the features the Scala detectors and the
ML scorer consume. Order-book-depth features (multilevel imbalance O13, VPIN O16) are added
once the generator emits Level-2 depth; the event-aggregate features here already cover the
spoofing / wash / order-to-trade signals.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def to_gold(silver: DataFrame, window_ms: int = 60_000) -> DataFrame:
    window_start = (F.floor(F.col("transact_time") / F.lit(window_ms)) * window_ms).cast("long")
    g = silver.withColumn("window_start", window_start)

    is_new = F.col("event_kind") == "NEW"
    return (
        g.groupBy("trader_id", "symbol", "window_start", "desk", "asset_class")
        .agg(
            F.sum(F.when(is_new, 1).otherwise(0)).alias("n_orders"),
            F.sum(F.when(F.col("event_kind") == "CANCEL", 1).otherwise(0)).alias("n_cancels"),
            F.sum(F.when(F.col("event_kind") == "EXEC", 1).otherwise(0)).alias("n_execs"),
            F.sum(F.when(is_new & F.col("is_buy"), F.col("order_qty")).otherwise(0)).alias("buy_qty"),
            F.sum(F.when(is_new & ~F.col("is_buy"), F.col("order_qty")).otherwise(0)).alias("sell_qty"),
            F.countDistinct("price").alias("distinct_prices"),
        )
        .withColumn("window_end", F.col("window_start") + F.lit(window_ms))
        .withColumn("cancel_ratio", F.col("n_cancels") / F.greatest(F.col("n_orders"), F.lit(1)))
        .withColumn("order_to_trade_ratio", F.col("n_orders") / F.greatest(F.col("n_execs"), F.lit(1)))
        .withColumn(
            "qty_imbalance",
            (F.col("buy_qty") - F.col("sell_qty"))
            / F.greatest(F.col("buy_qty") + F.col("sell_qty"), F.lit(1)),
        )
    )
