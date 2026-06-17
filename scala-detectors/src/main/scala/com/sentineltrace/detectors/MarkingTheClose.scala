package com.sentineltrace.detectors

import com.sentineltrace.{Alert, GoldFeatures}

/** Marking-the-close detector (UMIR 2.2 / MiFID II Art.12). Escalating BUY orders in the
  * closing window that walk the price up so the last print sets an inflated closing price.
  * The defining, non-cheatable signal is the CLOSE TIMING (secsToClose small) combined with an
  * upward price walk and the print landing at the window high. */
object MarkingTheClose {
  val Name = "MARKING_THE_CLOSE"
  val RegRefs: Seq[String] = Seq("UMIR_2.2", "MIFID_II_ART12")
  val Threshold = 0.5
  val CloseWindowSecs = 120.0

  def score(f: GoldFeatures): Double =
    if (
      f.secsToClose < 0.0 || f.secsToClose > CloseWindowSecs ||
      f.priceMoveBps <= 0.0 || f.nExecs < 1 || f.buyQty <= 0
    ) 0.0
    else {
      val closeProximity = 1.0 - math.min(f.secsToClose / CloseWindowSecs, 1.0) // 1.0 right at the bell
      val escalation = math.min(f.priceMoveBps / 5.0, 1.0)
      val printAtHigh = if (f.lastPx >= f.maxPx - 1e-9 && f.maxPx > 0) 1.0 else 0.5
      math.min(1.0, 0.3 + 0.3 * closeProximity + 0.2 * escalation + 0.2 * printAtHigh)
    }

  def detect(f: GoldFeatures, createdAt: Long): Option[Alert] =
    Emit.fromScore(Name, RegRefs, f, score(f), Threshold, createdAt)
}
