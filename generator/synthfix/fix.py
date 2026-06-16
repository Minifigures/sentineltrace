"""FIX 4.4 event model (JSON representation, not tag=value wire format).

The bronze lakehouse layer is a data lake, not a FIX engine, so messages are modeled
as dataclasses serialized to dicts/JSON with human-readable field names. Dependency-light
(stdlib only): no quickfix.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "1"
    SELL = "2"


class MsgType(str, Enum):
    NEW_ORDER_SINGLE = "D"
    EXECUTION_REPORT = "8"
    ORDER_CANCEL_REQUEST = "F"


class OrdType(str, Enum):
    MARKET = "1"
    LIMIT = "2"


class ExecType(str, Enum):
    NEW = "0"
    PARTIAL_FILL = "1"
    FILL = "2"
    CANCELLED = "4"


@dataclass
class FixEvent:
    """A single FIX event. Optional fields are dropped from the dict when None so each
    message type serializes to only its relevant tags."""

    msg_type: str
    cl_ord_id: str
    trader_id: str  # PII downstream
    account: str  # PII downstream
    symbol: str
    side: str
    order_qty: int
    ord_type: str
    transact_time: int  # epoch millis (UTC)
    exchange_id: str
    price: float | None = None
    # execution-report only
    exec_type: str | None = None
    order_id: str | None = None
    exec_id: str | None = None
    last_qty: int | None = None
    last_px: float | None = None
    # cancel only
    orig_cl_ord_id: str | None = None
    cancel_reason: str | None = None
    # provenance / labeling
    scenario_id: str | None = None
    scenario_type: str | None = None  # None == normal flow

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}
