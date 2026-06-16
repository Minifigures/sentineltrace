"""Labeled market-abuse scenarios. Each returns (events, ScenarioLabel) where the label
carries the ground-truth used for ML training and for the eval set. Scenarios are
deterministic given a seeded RNG + base timestamp, so the demo and tests are reproducible.

Mapped to regulation (UMIR / MiFID II) per scripts/spikes regulation tokens later.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .fix import ExecType, FixEvent, MsgType, OrdType, Side


@dataclass
class ScenarioLabel:
    scenario_id: str
    abuse_type: str  # SPOOFING | WASH_TRADE | ...
    trader_id: str
    instrument: str
    window_start: int  # epoch millis
    window_end: int
    injected_event_ids: list[str] = field(default_factory=list)


def spoofing(
    rng: random.Random,
    t0: int,
    trader_id: str,
    account: str,
    symbol: str,
    exchange: str,
    mid_price: float,
    scenario_id: str,
    layers: int = 4,
) -> tuple[list[FixEvent], ScenarioLabel]:
    """Layer large passive BUY orders below the touch to inflate the bid, execute a
    genuine SELL that benefits, then cancel the layered orders rapidly (UMIR 2.2 /
    MiFID II Art.12 manipulative layering)."""
    events: list[FixEvent] = []
    spoof_ids: list[str] = []

    for i in range(layers):
        cl = f"{scenario_id}-spoof-{i}"
        px = round(mid_price - (i + 1) * 0.01, 2)
        events.append(
            FixEvent(
                MsgType.NEW_ORDER_SINGLE.value, cl, trader_id, account, symbol,
                Side.BUY.value, 5000 + rng.randint(0, 500), OrdType.LIMIT.value,
                t0 + i * 50, exchange, price=px,
                scenario_id=scenario_id, scenario_type="SPOOFING",
            )
        )
        spoof_ids.append(cl)

    sell_cl = f"{scenario_id}-genuine-sell"
    sell_px = round(mid_price, 2)
    events.append(
        FixEvent(
            MsgType.NEW_ORDER_SINGLE.value, sell_cl, trader_id, account, symbol,
            Side.SELL.value, 200, OrdType.LIMIT.value, t0 + 300, exchange,
            price=sell_px, scenario_id=scenario_id, scenario_type="SPOOFING",
        )
    )
    events.append(
        FixEvent(
            MsgType.EXECUTION_REPORT.value, sell_cl, trader_id, account, symbol,
            Side.SELL.value, 200, OrdType.LIMIT.value, t0 + 350, exchange, price=sell_px,
            exec_type=ExecType.FILL.value, order_id=f"{scenario_id}-oid",
            exec_id=f"{scenario_id}-eid", last_qty=200, last_px=sell_px,
            scenario_id=scenario_id, scenario_type="SPOOFING",
        )
    )

    cancel_ids: list[str] = []
    for i, cl in enumerate(spoof_ids):
        ccl = f"{scenario_id}-cancel-{i}"
        events.append(
            FixEvent(
                MsgType.ORDER_CANCEL_REQUEST.value, ccl, trader_id, account, symbol,
                Side.BUY.value, 5000, OrdType.LIMIT.value, t0 + 400 + i * 20, exchange,
                orig_cl_ord_id=cl, cancel_reason="SPOOF_CANCEL",
                scenario_id=scenario_id, scenario_type="SPOOFING",
            )
        )
        cancel_ids.append(ccl)

    label = ScenarioLabel(
        scenario_id, "SPOOFING", trader_id, symbol, t0, t0 + 400 + layers * 20,
        spoof_ids + cancel_ids + [sell_cl],
    )
    return events, label


def wash_trade(
    rng: random.Random,
    t0: int,
    trader_id: str,
    account: str,
    symbol: str,
    exchange: str,
    mid_price: float,
    scenario_id: str,
) -> tuple[list[FixEvent], ScenarioLabel]:
    """Same trader places matching BUY and SELL at the same price/qty in a tight window
    so the order self-matches with no change in beneficial ownership (UMIR 2.2 wash trading)."""
    px = round(mid_price, 2)
    qty = 1000
    buy_cl = f"{scenario_id}-wash-buy"
    sell_cl = f"{scenario_id}-wash-sell"

    buy = FixEvent(
        MsgType.NEW_ORDER_SINGLE.value, buy_cl, trader_id, account, symbol,
        Side.BUY.value, qty, OrdType.LIMIT.value, t0, exchange, price=px,
        scenario_id=scenario_id, scenario_type="WASH_TRADE",
    )
    sell = FixEvent(
        MsgType.NEW_ORDER_SINGLE.value, sell_cl, trader_id, account, symbol,
        Side.SELL.value, qty, OrdType.LIMIT.value, t0 + 100, exchange, price=px,
        scenario_id=scenario_id, scenario_type="WASH_TRADE",
    )
    buy_fill = FixEvent(
        MsgType.EXECUTION_REPORT.value, buy_cl, trader_id, account, symbol,
        Side.BUY.value, qty, OrdType.LIMIT.value, t0 + 150, exchange, price=px,
        exec_type=ExecType.FILL.value, order_id=f"{scenario_id}-boid",
        exec_id=f"{scenario_id}-beid", last_qty=qty, last_px=px,
        scenario_id=scenario_id, scenario_type="WASH_TRADE",
    )
    sell_fill = FixEvent(
        MsgType.EXECUTION_REPORT.value, sell_cl, trader_id, account, symbol,
        Side.SELL.value, qty, OrdType.LIMIT.value, t0 + 150, exchange, price=px,
        exec_type=ExecType.FILL.value, order_id=f"{scenario_id}-soid",
        exec_id=f"{scenario_id}-seid", last_qty=qty, last_px=px,
        scenario_id=scenario_id, scenario_type="WASH_TRADE",
    )

    label = ScenarioLabel(
        scenario_id, "WASH_TRADE", trader_id, symbol, t0, t0 + 150, [buy_cl, sell_cl]
    )
    return [buy, sell, buy_fill, sell_fill], label
