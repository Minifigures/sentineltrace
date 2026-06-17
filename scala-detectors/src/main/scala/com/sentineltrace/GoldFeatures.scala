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
    qtyImbalance: Double,
    // price features (default 0.0 so older call sites and pre-enrichment rows still construct)
    firstPx: Double = 0.0,
    lastPx: Double = 0.0,
    minPx: Double = 0.0,
    maxPx: Double = 0.0,
    buyVwap: Double = 0.0,
    sellVwap: Double = 0.0,
    priceMoveBps: Double = 0.0,
    roundTripGainBps: Double = 0.0,
    secsToClose: Double = 1e9 // seconds from the window to session close; large == not near close
)
