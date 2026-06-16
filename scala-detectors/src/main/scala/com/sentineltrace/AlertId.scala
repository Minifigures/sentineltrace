package com.sentineltrace

/** Deterministic, cross-language alert id: SHA-256 of the dedupe tuple (detector, trader,
  * instrument, window) under the shared byte grammar, formatted UUID-like. Python reproduces
  * the same id with the same grammar + sha256, so demo deep-links and audits line up. */
object AlertId {
  def of(detector: String, traderId: String, instrument: String, windowStart: Long, windowEnd: Long): String = {
    val h = Hash.sha256Hex(Hash.canonicalBytes(Seq(detector, traderId, instrument, windowStart, windowEnd)))
    s"${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20, 32)}"
  }
}
