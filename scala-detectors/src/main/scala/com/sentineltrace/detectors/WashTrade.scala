package com.sentineltrace.detectors

import com.sentineltrace.{Alert, GoldFeatures}

/** Wash-trading detector (UMIR 2.2). Same trader on both sides with matched, executed,
  * price-concentrated volume and NO change in beneficial ownership: balanced quantity,
  * self-matched fills, few distinct prices, and ~zero realized gain (positive gain means
  * front-running, not wash). */
object WashTrade {
  val Name = "WASH_TRADE"
  val RegRefs: Seq[String] = Seq("UMIR_2.2", "MIFID_II_ART12")
  val Threshold = 0.6
  val MinExecs = 2L
  val MaxImbalance = 0.1
  val GainEpsBps = 1.0

  def score(f: GoldFeatures): Double =
    if (
      f.buyQty <= 0 || f.sellQty <= 0 || f.nExecs < MinExecs ||
      math.abs(f.qtyImbalance) > MaxImbalance || math.abs(f.roundTripGainBps) > GainEpsBps
    ) 0.0
    else {
      val balance = 1.0 - math.min(math.abs(f.qtyImbalance), 1.0)
      val priceConcentration = if (f.distinctPrices <= 2) 1.0 else 0.5
      math.max(0.0, math.min(1.0, 0.6 * balance + 0.4 * priceConcentration))
    }

  def detect(f: GoldFeatures, createdAt: Long): Option[Alert] =
    Emit.fromScore(Name, RegRefs, f, score(f), Threshold, createdAt)
}
