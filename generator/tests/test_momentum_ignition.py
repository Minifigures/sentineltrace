import random

import pytest

from synthfix.fix import ExecType, MsgType, OrdType, Side
from synthfix.scenarios import momentum_ignition


def test_momentum_ignition_abuse_type_and_metadata():
    rng = random.Random(42)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-1"
    )
    assert label.abuse_type == "MOMENTUM_IGNITION"
    assert label.trader_id == "trader-9"
    assert label.instrument == "TD"
    assert label.scenario_id == "sc-mi-1"


def test_momentum_ignition_burst_buys_are_aggressive():
    rng = random.Random(42)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-2",
        burst_size=5,
    )
    burst_news = [
        e for e in events
        if e.msg_type == MsgType.NEW_ORDER_SINGLE.value and e.side == Side.BUY.value
    ]
    # Exactly burst_size BUY new-order-singles.
    assert len(burst_news) == 5
    # All are limit orders priced at or above ask (mid + 0.01) — marketable-limit.
    ask = round(80.0 + 0.01, 2)
    assert all(b.price >= ask for b in burst_news)
    # Prices are strictly increasing (each successive order crosses a higher offer).
    prices = [b.price for b in burst_news]
    assert prices == sorted(prices)
    assert len(set(prices)) == len(prices)


def test_momentum_ignition_burst_fills_immediately_after_orders():
    rng = random.Random(42)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-3",
        burst_size=5,
    )
    buy_fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.BUY.value
        and e.exec_type == ExecType.FILL.value
    ]
    # One fill per burst order.
    assert len(buy_fills) == 5
    # Each fill carries a last_px at the order's limit price (taker fill at own limit).
    buy_news = [
        e for e in events
        if e.msg_type == MsgType.NEW_ORDER_SINGLE.value and e.side == Side.BUY.value
    ]
    for news, fill in zip(buy_news, buy_fills):
        assert fill.last_px == news.price
        # Fill arrives after the order.
        assert fill.transact_time > news.transact_time


def test_momentum_ignition_exit_sell_after_burst():
    rng = random.Random(42)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-4",
        burst_size=5,
        exit_qty=2000,
    )
    sell_fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.SELL.value
        and e.exec_type == ExecType.FILL.value
    ]
    assert len(sell_fills) == 1
    exit_fill = sell_fills[0]

    # Exit SELL is large.
    assert exit_fill.last_qty == 2000

    # Exit SELL is priced at the peak (ask + (burst_size-1)*0.01).
    expected_peak = round(80.0 + 0.01 + (5 - 1) * 0.01, 2)
    assert exit_fill.last_px == expected_peak

    # Exit SELL lands after all burst fills.
    burst_fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.BUY.value
    ]
    assert exit_fill.transact_time > max(f.transact_time for f in burst_fills)


def test_momentum_ignition_timestamps_are_ordered():
    rng = random.Random(99)
    events, label = momentum_ignition(
        rng, 2000000000000, "t", "a", "RY", "TSX", 50.0, "sc-mi-5"
    )
    times = [e.transact_time for e in events]
    assert times == sorted(times)


def test_momentum_ignition_window_bounds_cover_all_events():
    rng = random.Random(7)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-6"
    )
    assert label.window_start <= min(e.transact_time for e in events)
    assert label.window_end >= max(e.transact_time for e in events)


def test_momentum_ignition_all_events_carry_scenario_tag():
    rng = random.Random(3)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-7"
    )
    assert all(e.scenario_id == "sc-mi-7" for e in events)
    assert all(e.scenario_type == "MOMENTUM_IGNITION" for e in events)


def test_momentum_ignition_injected_ids_reference_real_events():
    rng = random.Random(11)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-8"
    )
    all_cl_ord_ids = {e.cl_ord_id for e in events}
    assert set(label.injected_event_ids) <= all_cl_ord_ids


def test_momentum_ignition_injected_ids_are_burst_plus_exit():
    rng = random.Random(55)
    burst_size = 6
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-9",
        burst_size=burst_size,
    )
    # burst_size BUY orders + 1 exit SELL = burst_size + 1 injected ids.
    assert len(label.injected_event_ids) == burst_size + 1
    # The exit sell id ends with "-exit-sell".
    exit_ids = [i for i in label.injected_event_ids if i.endswith("-exit-sell")]
    assert len(exit_ids) == 1


def test_momentum_ignition_is_deterministic():
    a, _ = momentum_ignition(
        random.Random(1), 1000, "t", "a", "RY", "TSX", 10.0, "s1"
    )
    b, _ = momentum_ignition(
        random.Random(1), 1000, "t", "a", "RY", "TSX", 10.0, "s1"
    )
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]


def test_momentum_ignition_custom_burst_size():
    rng = random.Random(77)
    events, label = momentum_ignition(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mi-10",
        burst_size=3,
    )
    buy_news = [
        e for e in events
        if e.msg_type == MsgType.NEW_ORDER_SINGLE.value and e.side == Side.BUY.value
    ]
    assert len(buy_news) == 3
    assert len(label.injected_event_ids) == 4  # 3 burst + 1 exit
