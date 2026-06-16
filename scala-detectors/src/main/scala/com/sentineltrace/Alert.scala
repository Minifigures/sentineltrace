package com.sentineltrace

/** Scala mirror of the canonical Alert contract (pipeline/shared/models/alert_contract.py).
  * Kept in lockstep by the cross-language contract-sync test. Field order matches the master. */
final case class FeatureContribution(
    featureName: String,
    featureValue: Double,
    shapValue: Double,
    rank: Int,
    direction: String
)

final case class Alert(
    alertId: String,
    detector: String,
    traderId: String,
    instrument: String,
    windowStart: Long,
    windowEnd: Long,
    severity: Int,
    ruleScore: Double,
    mlScore: Option[Double],
    shapTopFeatures: Seq[FeatureContribution],
    triggeringEventIds: Seq[String],
    regulationRefs: Seq[String],
    desk: String,
    createdAt: Long,
    auditHash: String
)
