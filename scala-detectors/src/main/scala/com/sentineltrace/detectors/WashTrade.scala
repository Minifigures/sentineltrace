package com.sentineltrace.detectors

import com.sentineltrace.{Alert, AlertId, GoldFeatures, Hash, Severity}

/** Wash-trading detector (UMIR 2.2). Same trader on both sides with matched, executed,
  * price-concentrated volume and no change in beneficial ownership: high balance (qty
  * imbalance near zero) + both sides present + self-matched fills + few distinct prices. */
object WashTrade {
  val Name = "WASH_TRADE"
  val RegRefs: Seq[String] = Seq("UMIR_2.2", "MIFID_II_ART12")
  val Threshold = 0.6
  val MinExecs = 2L

  def score(f: GoldFeatures): Double =
    if (f.buyQty <= 0 || f.sellQty <= 0 || f.nExecs < MinExecs) 0.0
    else {
      val balance = 1.0 - math.min(math.abs(f.qtyImbalance), 1.0) // 1.0 when perfectly balanced
      val priceConcentration = if (f.distinctPrices <= 2) 1.0 else 0.5
      math.max(0.0, math.min(1.0, 0.6 * balance + 0.4 * priceConcentration))
    }

  def detect(f: GoldFeatures, createdAt: Long): Option[Alert] = {
    val s = score(f)
    if (s < Threshold) None
    else {
      val sev = Severity.fromRuleScore(s)
      val id = AlertId.of(Name, f.traderId, f.instrument, f.windowStart, f.windowEnd)
      val auditHash = Hash.sha256Hex(
        Hash.canonicalBytes(
          Seq(id, Name, f.traderId, f.instrument, f.windowStart, f.windowEnd, sev, s,
            null, Seq.empty[String], RegRefs, f.desk, createdAt)
        )
      )
      Some(
        Alert(id, Name, f.traderId, f.instrument, f.windowStart, f.windowEnd, sev, s,
          None, Seq.empty, Seq.empty, RegRefs, f.desk, createdAt, auditHash)
      )
    }
  }
}
