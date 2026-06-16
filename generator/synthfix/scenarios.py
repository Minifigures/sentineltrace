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


def front_running(
    rng: random.Random,
    t0: int,
    trader_id: str,
    account: str,
    symbol: str,
    exchange: str,
    mid_price: float,
    scenario_id: str,
    client_qty: int = 10000,
) -> tuple[list[FixEvent], ScenarioLabel]:
    """Abuser detects a large incoming client BUY and pre-positions a BUY just ahead,
    gets filled at the pre-move price, then the client order executes and pushes the
    price up so the abuser immediately profits (UMIR 4.1 / MiFID II Art.12 front-running).

    Timeline (all offsets from t0):
      +0   ms  client submits large BUY (benign context)
      +50  ms  abuser places own BUY ahead of client, same or slightly higher price
      +100 ms  abuser BUY fills at the pre-move price
      +200 ms  client large BUY hits market and fills, moving price up
      +300 ms  abuser sells at the higher post-move price, realising the profit

    injected_event_ids = abuser pre-positioning NEW_ORDER_SINGLE + its EXECUTION_REPORT
    (the manipulative acts); client order and abuser exit sale are benign context / outcome.
    """
    events: list[FixEvent] = []

    client_id = f"{scenario_id}-client"
    client_cl = f"{scenario_id}-client-buy"
    abuser_cl = f"{scenario_id}-abuser-buy"
    abuser_exit_cl = f"{scenario_id}-abuser-sell"

    entry_px = round(mid_price, 2)
    abuser_qty = 500 + rng.randint(0, 200)
    post_move_px = round(mid_price + rng.uniform(0.05, 0.20), 2)

    # --- benign context: client submits large BUY ---
    events.append(
        FixEvent(
            MsgType.NEW_ORDER_SINGLE.value, client_cl, client_id, f"{scenario_id}-client-acc",
            symbol, Side.BUY.value, client_qty, OrdType.MARKET.value,
            t0, exchange,
            scenario_id=scenario_id, scenario_type="FRONT_RUNNING",
        )
    )

    # --- manipulative: abuser pre-positions BUY ahead of client ---
    events.append(
        FixEvent(
            MsgType.NEW_ORDER_SINGLE.value, abuser_cl, trader_id, account,
            symbol, Side.BUY.value, abuser_qty, OrdType.LIMIT.value,
            t0 + 50, exchange, price=entry_px,
            scenario_id=scenario_id, scenario_type="FRONT_RUNNING",
        )
    )

    # --- manipulative: abuser BUY fills at pre-move price ---
    events.append(
        FixEvent(
            MsgType.EXECUTION_REPORT.value, abuser_cl, trader_id, account,
            symbol, Side.BUY.value, abuser_qty, OrdType.LIMIT.value,
            t0 + 100, exchange, price=entry_px,
            exec_type=ExecType.FILL.value,
            order_id=f"{scenario_id}-abuser-oid",
            exec_id=f"{scenario_id}-abuser-eid",
            last_qty=abuser_qty, last_px=entry_px,
            scenario_id=scenario_id, scenario_type="FRONT_RUNNING",
        )
    )

    # --- benign context: client large BUY executes, moves price up ---
    events.append(
        FixEvent(
            MsgType.EXECUTION_REPORT.value, client_cl, client_id, f"{scenario_id}-client-acc",
            symbol, Side.BUY.value, client_qty, OrdType.MARKET.value,
            t0 + 200, exchange, price=entry_px,
            exec_type=ExecType.FILL.value,
            order_id=f"{scenario_id}-client-oid",
            exec_id=f"{scenario_id}-client-eid",
            last_qty=client_qty, last_px=entry_px,
            scenario_id=scenario_id, scenario_type="FRONT_RUNNING",
        )
    )

    # --- abuser exit: sell at post-move price to realise profit ---
    events.append(
        FixEvent(
            MsgType.NEW_ORDER_SINGLE.value, abuser_exit_cl, trader_id, account,
            symbol, Side.SELL.value, abuser_qty, OrdType.LIMIT.value,
            t0 + 300, exchange, price=post_move_px,
            scenario_id=scenario_id, scenario_type="FRONT_RUNNING",
        )
    )
    events.append(
        FixEvent(
            MsgType.EXECUTION_REPORT.value, abuser_exit_cl, trader_id, account,
            symbol, Side.SELL.value, abuser_qty, OrdType.LIMIT.value,
            t0 + 350, exchange, price=post_move_px,
            exec_type=ExecType.FILL.value,
            order_id=f"{scenario_id}-abuser-exit-oid",
            exec_id=f"{scenario_id}-abuser-exit-eid",
            last_qty=abuser_qty, last_px=post_move_px,
            scenario_id=scenario_id, scenario_type="FRONT_RUNNING",
        )
    )

    label = ScenarioLabel(
        scenario_id, "FRONT_RUNNING", trader_id, symbol,
        t0, t0 + 350,
        [abuser_cl],
    )
    return events, label


def momentum_ignition(
    rng: random.Random,
    t0: int,
    trader_id: str,
    account: str,
    symbol: str,
    exchange: str,
    mid_price: float,
    scenario_id: str,
    burst_size: int = 5,
    exit_qty: int = 2000,
) -> tuple[list[FixEvent], ScenarioLabel]:
    """Fire a rapid burst of aggressive BUY orders to ignite an upward price move,
    then exit with a large SELL into the elevated momentum (UMIR 2.2 / MiFID II Art.12).

    Phase 1 — Ignition burst: burst_size marketable-limit BUY orders sent 80 ms apart,
    each filled immediately at a price that ticks up by 0.01 per fill, simulating the
    momentum cascade induced in other market participants.

    Phase 2 — Exit: one large LIMIT SELL placed after the burst fills have landed,
    executed at the peak inflated price to harvest the manufactured move.

    injected_event_ids contains the cl_ord_id of every burst BUY and the exit SELL
    (the abuser's manipulative orders); execution-report events are excluded because
    they are reactive confirmations, not the manipulative acts themselves.
    """
    events: list[FixEvent] = []
    burst_ids: list[str] = []

    # --- Phase 1: ignition burst ---
    # Marketable-limit BUYs priced at or above the ask to guarantee immediate fills.
    # Price steps up by 0.01 per order to model the abuser lifting the offer aggressively.
    ask = round(mid_price + 0.01, 2)

    for i in range(burst_size):
        cl = f"{scenario_id}-burst-{i}"
        # Each successive order is priced one tick higher to keep crossing the rising offer.
        px = round(ask + i * 0.01, 2)
        qty = 200 + rng.randint(0, 100)
        t_new = t0 + i * 80

        events.append(
            FixEvent(
                MsgType.NEW_ORDER_SINGLE.value, cl, trader_id, account, symbol,
                Side.BUY.value, qty, OrdType.LIMIT.value, t_new, exchange, price=px,
                scenario_id=scenario_id, scenario_type="MOMENTUM_IGNITION",
            )
        )

        # Immediate fill at the order's limit price (taker crosses the spread).
        fill_px = px
        events.append(
            FixEvent(
                MsgType.EXECUTION_REPORT.value, cl, trader_id, account, symbol,
                Side.BUY.value, qty, OrdType.LIMIT.value, t_new + 20, exchange,
                price=fill_px,
                exec_type=ExecType.FILL.value,
                order_id=f"{scenario_id}-boid-{i}",
                exec_id=f"{scenario_id}-beid-{i}",
                last_qty=qty, last_px=fill_px,
                scenario_id=scenario_id, scenario_type="MOMENTUM_IGNITION",
            )
        )

        burst_ids.append(cl)

    # --- Phase 2: exit SELL into elevated market ---
    # Placed after all burst fills; priced at the peak the ignition reached.
    peak_px = round(ask + (burst_size - 1) * 0.01, 2)
    exit_cl = f"{scenario_id}-exit-sell"
    t_exit = t0 + burst_size * 80 + 150

    events.append(
        FixEvent(
            MsgType.NEW_ORDER_SINGLE.value, exit_cl, trader_id, account, symbol,
            Side.SELL.value, exit_qty, OrdType.LIMIT.value, t_exit, exchange,
            price=peak_px,
            scenario_id=scenario_id, scenario_type="MOMENTUM_IGNITION",
        )
    )
    events.append(
        FixEvent(
            MsgType.EXECUTION_REPORT.value, exit_cl, trader_id, account, symbol,
            Side.SELL.value, exit_qty, OrdType.LIMIT.value, t_exit + 30, exchange,
            price=peak_px,
            exec_type=ExecType.FILL.value,
            order_id=f"{scenario_id}-soid",
            exec_id=f"{scenario_id}-seid",
            last_qty=exit_qty, last_px=peak_px,
            scenario_id=scenario_id, scenario_type="MOMENTUM_IGNITION",
        )
    )

    window_end = t_exit + 30
    label = ScenarioLabel(
        scenario_id, "MOMENTUM_IGNITION", trader_id, symbol, t0, window_end,
        burst_ids + [exit_cl],
    )
    return events, label


def marking_the_close(
    rng: random.Random,
    t0: int,
    trader_id: str,
    account: str,
    symbol: str,
    exchange: str,
    mid_price: float,
    scenario_id: str,
    waves: int = 3,
) -> tuple[list[FixEvent], ScenarioLabel]:
    """Place escalating-price BUY limit orders in the final minute before market close so
    that the last trade prints at an artificially high closing price (UMIR 2.2 / MiFID II
    Art.12).  t0 is treated as the epoch-millis timestamp ~60 s before the session close.

    Pattern
    -------
    1. For each wave i in [0, waves): submit a BUY limit at mid_price + (i+1)*0.01 with
       a moderate qty.  Each successive order sits above the previous one, walking the price
       up.  Orders are spaced ~15 s apart in the closing window.
    2. The final wave order receives a FILL execution report -- that print becomes the
       official closing price, inflated above fair value.
    3. Earlier waves are cancelled immediately after the final fill (they served their
       price-walking purpose and the trader does not want residual risk).

    injected_event_ids includes every closing-window NEW_ORDER_SINGLE plus the final fill
    execution report.
    """
    events: list[FixEvent] = []
    wave_ids: list[str] = []

    # spacing: spread waves evenly across the last 45 s of the closing window
    spacing_ms = 15_000  # 15 s between wave orders

    for i in range(waves):
        cl = f"{scenario_id}-mtc-{i}"
        px = round(mid_price + (i + 1) * 0.01, 2)
        qty = 500 + rng.randint(0, 200)
        events.append(
            FixEvent(
                MsgType.NEW_ORDER_SINGLE.value, cl, trader_id, account, symbol,
                Side.BUY.value, qty, OrdType.LIMIT.value,
                t0 + i * spacing_ms, exchange, price=px,
                scenario_id=scenario_id, scenario_type="MARKING_THE_CLOSE",
            )
        )
        wave_ids.append(cl)

    # final wave fills -- this becomes the closing print
    final_cl = wave_ids[-1]
    final_px = round(mid_price + waves * 0.01, 2)
    final_qty = events[-1].order_qty
    fill_time = t0 + (waves - 1) * spacing_ms + 500  # 500 ms after the final order lands
    fill_cl_ord_id = f"{scenario_id}-mtc-fill"
    events.append(
        FixEvent(
            MsgType.EXECUTION_REPORT.value, final_cl, trader_id, account, symbol,
            Side.BUY.value, final_qty, OrdType.LIMIT.value,
            fill_time, exchange, price=final_px,
            exec_type=ExecType.FILL.value,
            order_id=f"{scenario_id}-oid",
            exec_id=f"{scenario_id}-eid",
            last_qty=final_qty, last_px=final_px,
            scenario_id=scenario_id, scenario_type="MARKING_THE_CLOSE",
        )
    )

    # cancel earlier waves after the final fill (residual-risk cleanup)
    cancel_ids: list[str] = []
    for i, cl in enumerate(wave_ids[:-1]):
        ccl = f"{scenario_id}-mtc-cancel-{i}"
        events.append(
            FixEvent(
                MsgType.ORDER_CANCEL_REQUEST.value, ccl, trader_id, account, symbol,
                Side.BUY.value, events[i].order_qty, OrdType.LIMIT.value,
                fill_time + 200 + i * 50, exchange,
                orig_cl_ord_id=cl, cancel_reason="POST_CLOSE_CLEANUP",
                scenario_id=scenario_id, scenario_type="MARKING_THE_CLOSE",
            )
        )
        cancel_ids.append(ccl)

    window_end = fill_time + 200 + max(len(wave_ids[:-1]) - 1, 0) * 50
    label = ScenarioLabel(
        scenario_id, "MARKING_THE_CLOSE", trader_id, symbol, t0, window_end,
        wave_ids + [final_cl],
    )
    return events, label


