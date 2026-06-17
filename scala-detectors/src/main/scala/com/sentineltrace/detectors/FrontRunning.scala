package com.sentineltrace.detectors

import com.sentineltrace.{Alert, GoldFeatures}

/** Front-running detector (UMIR 4.1 / MiFID II Art.12). The abuser pre-positions ahead of a
  * large order and closes the position for a realized gain in the same window: a balanced
  * round trip (buy and sell quantity match) that is executed and ends with a POSITIVE round-trip
  * gain. The positive gain is what separates it from wash trading (which nets to zero). */
object FrontRunning {
  val Name = "FRONT_RUNNING"
  val RegRefs: Seq[String] = Seq("UMIR_4.1", "MIFID_II_ART12")
  val Threshold = 0.5
  val MinExecs = 2L
  val MaxImbalance = 0.1
  val MinGainBps = 1.0

  def score(f: GoldFeatures): Double =
    if (
      f.nExecs < MinExecs || math.abs(f.qtyImbalance) > MaxImbalance ||
      f.roundTripGainBps <= MinGainBps || f.buyQty <= 0 || f.sellQty <= 0
    ) 0.0
    else math.min(1.0, 0.6 + 0.4 * math.min(f.roundTripGainBps / 10.0, 1.0))

  def detect(f: GoldFeatures, createdAt: Long): Option[Alert] =
    Emit.fromScore(Name, RegRefs, f, score(f), Threshold, createdAt)
}
