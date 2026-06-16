package com.sentineltrace

/** Severity is DETECTOR-OWNED and a pure function of ruleScore, so an auditor can reproduce
  * it with no model in the loop: ceil(ruleScore * 5), clamped to [floor, 5]. */
object Severity {
  def fromRuleScore(ruleScore: Double, floor: Int = 1): Int = {
    val raw = math.ceil(ruleScore * 5.0).toInt
    math.min(5, math.max(floor, math.max(1, raw)))
  }
}
