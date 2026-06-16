package com.sentineltrace

/** One per-(trader, instrument, window) gold feature row, mirroring the PySpark gold schema
  * (pipeline/transforms/gold.py). Detectors consume this. */
final case class GoldFeatures(
    traderId: String,
    instrument: String,
    windowStart: Long,
    windowEnd: Long,
    desk: String,
    assetClass: String,
    nOrders: Long,
    nCancels: Long,
    nExecs: Long,
    buyQty: Long,
    sellQty: Long,
    distinctPrices: Long,
    cancelRatio: Double,
    orderToTradeRatio: Double,
    qtyImbalance: Double
)
