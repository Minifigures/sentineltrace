"""Gold layer: per-(trader, instrument, time-window) surveillance features.

Pure-function aggregation over silver. These are the features the Scala detectors and the
ML scorer consume. Event-aggregate features (counts, ratios, imbalance) plus price features
(first/last/min/max, price move, side VWAPs, round-trip gain) which together separate the
five abuse archetypes. Order-book-depth features (multilevel imbalance O13, VPIN O16) are
added once the generator emits Level-2 depth.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

_KEYS = ["trader_id", "symbol", "window_start"]


def to_gold(silver: DataFrame, window_ms: int = 60_000) -> DataFrame:
    window_start = (F.floor(F.col("transact_time") / F.lit(window_ms)) * window_ms).cast("long")
    g = silver.withColumn("window_start", window_start)
    is_new = F.col("event_kind") == "NEW"
    is_exec = F.col("event_kind") == "EXEC"

    base = (
        g.groupBy("trader_id", "symbol", "window_start", "desk", "asset_class")
        .agg(
            F.sum(F.when(is_new, 1).otherwise(0)).alias("n_orders"),
            F.sum(F.when(F.col("event_kind") == "CANCEL", 1).otherwise(0)).alias("n_cancels"),
            F.sum(F.when(is_exec, 1).otherwise(0)).alias("n_execs"),
            F.sum(F.when(is_new & F.col("is_buy"), F.col("order_qty")).otherwise(0)).alias("buy_qty"),
            F.sum(F.when(is_new & ~F.col("is_buy"), F.col("order_qty")).otherwise(0)).alias("sell_qty"),
            F.countDistinct("price").alias("distinct_prices"),
        )
    )

    # price features over priced rows (cancels carry no price)
    priced = g.filter(F.col("price").isNotNull())
    px = priced.groupBy(*_KEYS).agg(
        F.min_by("price", "transact_time").alias("first_px"),
        F.max_by("price", "transact_time").alias("last_px"),
        F.min("price").alias("min_px"),
        F.max("price").alias("max_px"),
    )

    # side VWAPs over executions (use fill price/qty)
    execs = g.filter(is_exec & F.col("last_px").isNotNull() & F.col("last_qty").isNotNull())
    vwap = execs.groupBy(*_KEYS).agg(
        (
            F.sum(F.when(F.col("is_buy"), F.col("last_qty") * F.col("last_px")))
            / F.sum(F.when(F.col("is_buy"), F.col("last_qty")))
        ).alias("buy_vwap"),
        (
            F.sum(F.when(~F.col("is_buy"), F.col("last_qty") * F.col("last_px")))
            / F.sum(F.when(~F.col("is_buy"), F.col("last_qty")))
        ).alias("sell_vwap"),
    )

    out = (
        base.join(px, _KEYS, "left").join(vwap, _KEYS, "left")
        .withColumn("window_end", F.col("window_start") + F.lit(window_ms))
        .withColumn("first_px", F.coalesce("first_px", F.lit(0.0)))
        .withColumn("last_px", F.coalesce("last_px", F.lit(0.0)))
        .withColumn("min_px", F.coalesce("min_px", F.lit(0.0)))
        .withColumn("max_px", F.coalesce("max_px", F.lit(0.0)))
        .withColumn("buy_vwap", F.coalesce("buy_vwap", F.lit(0.0)))
        .withColumn("sell_vwap", F.coalesce("sell_vwap", F.lit(0.0)))
        .withColumn("cancel_ratio", F.col("n_cancels") / F.greatest(F.col("n_orders"), F.lit(1)))
        .withColumn("order_to_trade_ratio", F.col("n_orders") / F.greatest(F.col("n_execs"), F.lit(1)))
        .withColumn(
            "qty_imbalance",
            (F.col("buy_qty") - F.col("sell_qty"))
            / F.greatest(F.col("buy_qty") + F.col("sell_qty"), F.lit(1)),
        )
        .withColumn(
            "price_move_bps",
            F.when(F.col("first_px") > 0, (F.col("last_px") - F.col("first_px")) / F.col("first_px") * 10000.0).otherwise(0.0),
        )
        .withColumn(
            "round_trip_gain_bps",
            F.when(
                (F.col("buy_vwap") > 0) & (F.col("sell_vwap") > 0),
                (F.col("sell_vwap") - F.col("buy_vwap")) / F.col("buy_vwap") * 10000.0,
            ).otherwise(0.0),
        )
    )
    return out
