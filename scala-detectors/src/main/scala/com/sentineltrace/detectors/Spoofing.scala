package com.sentineltrace.detectors

import com.sentineltrace.{Alert, GoldFeatures}

/** Spoofing / layering detector (UMIR 2.2 / MiFID II Art.12). Scores a gold feature window:
  * dominated by cancel_ratio (place-and-cancel the manipulative signal), amplified by a high
  * order-to-trade ratio, gated by a minimum order count to avoid firing on thin activity. */
object Spoofing {
  val Name = "SPOOFING"
  val RegRefs: Seq[String] = Seq("UMIR_2.2", "MIFID_II_ART12")
  val Threshold = 0.5
  val MinOrders = 4L

  /** Pure rule score in [0,1]. */
  def score(f: GoldFeatures): Double =
    if (f.nOrders < MinOrders) 0.0
    else {
      val ott = math.min(f.orderToTradeRatio / 10.0, 1.0)
      math.max(0.0, math.min(1.0, 0.7 * f.cancelRatio + 0.3 * ott))
    }

  def detect(f: GoldFeatures, createdAt: Long): Option[Alert] =
    Emit.fromScore(Name, RegRefs, f, score(f), Threshold, createdAt)
}
