package com.sentineltrace.detectors

import com.sentineltrace.{Alert, AlertId, GoldFeatures, Hash, Severity}

/** Shared alert construction: turns a rule score into a canonical Alert with the deterministic
  * alert id and the chain-ready audit hash. The hashed field order matches ALERT_HASH_FIELD_ORDER
  * in alert_contract.py so detector audit hashes verify in the same chain as every other subsystem. */
object Emit {
  def fromScore(
      name: String,
      regRefs: Seq[String],
      f: GoldFeatures,
      ruleScore: Double,
      threshold: Double,
      createdAt: Long
  ): Option[Alert] =
    if (ruleScore < threshold) None
    else {
      val sev = Severity.fromRuleScore(ruleScore)
      val id = AlertId.of(name, f.traderId, f.instrument, f.windowStart, f.windowEnd)
      val auditHash = Hash.sha256Hex(
        Hash.canonicalBytes(
          Seq(id, name, f.traderId, f.instrument, f.windowStart, f.windowEnd, sev, ruleScore,
            null, Seq.empty[String], regRefs, f.desk, createdAt)
        )
      )
      Some(
        Alert(id, name, f.traderId, f.instrument, f.windowStart, f.windowEnd, sev, ruleScore,
          None, Seq.empty, Seq.empty, regRefs, f.desk, createdAt, auditHash)
      )
    }
}
