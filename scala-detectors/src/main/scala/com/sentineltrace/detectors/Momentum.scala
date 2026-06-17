package com.sentineltrace.detectors

import com.sentineltrace.{Alert, GoldFeatures}

/** Momentum-ignition detector (UMIR 2.2 / MiFID II Art.12). A rapid burst of aggressive,
  * immediately-filled same-side orders that walks the price up, followed by a large opposite
  * exit into the manufactured move: many fills (not cancels), positive price move, low cancels. */
object Momentum {
  val Name = "MOMENTUM_IGNITION"
  val RegRefs: Seq[String] = Seq("UMIR_2.2", "MIFID_II_ART12")
  val Threshold = 0.5
  val MinExecs = 4L
  val MaxCancelRatio = 0.2

  def score(f: GoldFeatures): Double =
    if (f.nExecs < MinExecs || f.priceMoveBps <= 0.0 || f.cancelRatio > MaxCancelRatio || f.sellQty <= 0) 0.0
    else {
      val fillIntensity = math.min(f.nExecs / 6.0, 1.0)
      val moveConfirm = math.min(f.priceMoveBps / 5.0, 1.0)
      math.min(1.0, 0.4 * fillIntensity + 0.3 + 0.1 * moveConfirm)
    }

  def detect(f: GoldFeatures, createdAt: Long): Option[Alert] =
    Emit.fromScore(Name, RegRefs, f, score(f), Threshold, createdAt)
}
