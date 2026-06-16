import random

import pytest

from synthfix.fix import ExecType, MsgType, OrdType, Side
from synthfix.scenarios import front_running


def test_front_running_abuse_type_and_metadata():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    assert label.abuse_type == "FRONT_RUNNING"
    assert label.trader_id == "trader-9"
    assert label.instrument == "TD"
    assert label.scenario_id == "sc-fr-1"


def test_front_running_injected_ids_reference_real_events():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    all_cl_ord_ids = {e.cl_ord_id for e in events}
    assert set(label.injected_event_ids) <= all_cl_ord_ids
    assert len(label.injected_event_ids) >= 1


def test_front_running_injected_ids_are_abuser_orders_not_client():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    client_id = "sc-fr-1-client"
    injected_events = [e for e in events if e.cl_ord_id in label.injected_event_ids]
    assert all(e.trader_id != client_id for e in injected_events)
    assert all(e.trader_id == "trader-9" for e in injected_events)


def test_front_running_abuser_buys_before_client_fills():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    abuser_buy_news = [
        e for e in events
        if e.msg_type == MsgType.NEW_ORDER_SINGLE.value
        and e.side == Side.BUY.value
        and e.trader_id == "trader-9"
    ]
    assert len(abuser_buy_news) == 1

    client_fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.BUY.value
        and e.exec_type == ExecType.FILL.value
        and e.trader_id != "trader-9"
    ]
    assert len(client_fills) == 1
    assert abuser_buy_news[0].transact_time < client_fills[0].transact_time


def test_front_running_abuser_fills_before_client_fills():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    abuser_buy_fill = next(
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.BUY.value
        and e.exec_type == ExecType.FILL.value
        and e.trader_id == "trader-9"
    )
    client_fill = next(
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.BUY.value
        and e.exec_type == ExecType.FILL.value
        and e.trader_id != "trader-9"
    )
    assert abuser_buy_fill.transact_time < client_fill.transact_time


def test_front_running_abuser_exit_sell_at_higher_price():
    rng = random.Random(42)
    mid = 80.0
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", mid, "sc-fr-1"
    )
    abuser_buy_fill = next(
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.BUY.value
        and e.exec_type == ExecType.FILL.value
        and e.trader_id == "trader-9"
    )
    abuser_sell_fill = next(
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.SELL.value
        and e.exec_type == ExecType.FILL.value
        and e.trader_id == "trader-9"
    )
    assert abuser_sell_fill.last_px > abuser_buy_fill.last_px
    assert abuser_sell_fill.transact_time > abuser_buy_fill.transact_time


def test_front_running_client_order_not_in_injected_ids():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    client_cl = "sc-fr-1-client-buy"
    assert client_cl not in label.injected_event_ids


def test_front_running_timestamps_are_monotonically_ordered():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    times = [e.transact_time for e in events]
    assert times == sorted(times)
    assert label.window_start <= times[0]
    assert label.window_end >= times[-1]


def test_front_running_all_events_carry_scenario_metadata():
    rng = random.Random(42)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-1"
    )
    for e in events:
        assert e.scenario_id == "sc-fr-1"
        assert e.scenario_type == "FRONT_RUNNING"


def test_front_running_is_deterministic():
    a, _ = front_running(random.Random(7), 2000000, "t", "a", "BNS", "TSX", 50.0, "s-det")
    b, _ = front_running(random.Random(7), 2000000, "t", "a", "BNS", "TSX", 50.0, "s-det")
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]


def test_front_running_client_qty_kwarg():
    rng = random.Random(99)
    events, label = front_running(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-fr-cq",
        client_qty=25000,
    )
    client_news = [
        e for e in events
        if e.msg_type == MsgType.NEW_ORDER_SINGLE.value
        and e.trader_id == "sc-fr-cq-client"
    ]
    assert len(client_news) == 1
    assert client_news[0].order_qty == 25000
