"""Canonical Alert contract — the single source of truth for the alert shape.

This is the MASTER definition. The PySpark StructType (pipeline/conf/schemas.py),
the Scala case class (scala-detectors/.../Alert.scala), and the TypeScript interface
(web/lib/types.ts) are MIRRORS of this file and are kept in lockstep by the
contract-sync test (tests/contract/). Any field/type/order drift fails CI.

Six subsystems consume this shape: detectors, ML, governance, agent, web, tests.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Detector(str, Enum):
    SPOOFING = "SPOOFING"
    WASH_TRADE = "WASH_TRADE"
    FRONT_RUNNING = "FRONT_RUNNING"
    MOMENTUM_IGNITION = "MOMENTUM_IGNITION"
    MARKING_THE_CLOSE = "MARKING_THE_CLOSE"


class Desk(str, Enum):
    EQUITY = "equity"
    DERIVATIVES = "derivatives"


class FeatureContribution(BaseModel):
    """One SHAP feature attribution. Exactly five fields (locked)."""

    feature_name: str
    feature_value: float
    shap_value: float
    rank: int = Field(ge=1)
    direction: str  # "increases" | "decreases"


class Alert(BaseModel):
    """The canonical surveillance alert. Field ORDER here is contract-significant
    (it defines the audit-hash byte grammar; see docs/audit-byte-grammar.md)."""

    alert_id: str  # deterministic UUIDv5 of (detector, trader_id, instrument, window_start, window_end)
    detector: Detector
    trader_id: str  # PII — masked downstream via Unity Catalog
    instrument: str
    window_start: int  # epoch millis (UTC)
    window_end: int  # epoch millis (UTC)
    severity: int = Field(ge=1, le=5)  # detector-owned, pure function of rule_score
    rule_score: float = Field(ge=0.0, le=1.0)  # authoritative, reproducible with no model
    ml_score: float | None = Field(default=None, ge=0.0, le=1.0)  # filled by ML layer
    shap_top_features: list[FeatureContribution] = Field(default_factory=list)
    triggering_event_ids: list[str] = Field(default_factory=list)
    regulation_refs: list[str] = Field(default_factory=list)  # canonical tokens from reg_map
    desk: Desk
    created_at: int  # epoch millis (UTC)
    audit_hash: str  # hex digest linking this alert into the audit chain


# Frozen field order used by the audit-hash byte grammar. Changing this is a
# breaking contract change and must update docs/audit-byte-grammar.md + golden fixtures.
ALERT_HASH_FIELD_ORDER: tuple[str, ...] = (
    "alert_id",
    "detector",
    "trader_id",
    "instrument",
    "window_start",
    "window_end",
    "severity",
    "rule_score",
    "ml_score",
    "triggering_event_ids",
    "regulation_refs",
    "desk",
    "created_at",
)
