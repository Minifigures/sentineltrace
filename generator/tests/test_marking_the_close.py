import random

from synthfix.fix import ExecType, MsgType, OrdType, Side
from synthfix.scenarios import marking_the_close


def test_marking_the_close_escalating_prices():
    rng = random.Random(99)
    events, label = marking_the_close(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mtc-1"
    )

    assert label.abuse_type == "MARKING_THE_CLOSE"
    assert label.trader_id == "trader-9"
    assert label.instrument == "TD"

    # all closing-window orders are BUY limits
    new_orders = [
        e for e in events
        if e.msg_type == MsgType.NEW_ORDER_SINGLE.value
        and e.scenario_type == "MARKING_THE_CLOSE"
    ]
    assert len(new_orders) >= 2
    assert all(e.side == Side.BUY.value for e in new_orders)
    assert all(e.ord_type == OrdType.LIMIT.value for e in new_orders)

    # prices are strictly escalating across successive waves
    prices = [e.price for e in new_orders]
    assert prices == sorted(prices) and len(set(prices)) == len(prices)

    # final wave is priced above mid
    mid = 80.0
    assert new_orders[-1].price > mid


def test_marking_the_close_closing_print_is_highest():
    rng = random.Random(42)
    events, label = marking_the_close(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mtc-2"
    )

    fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.exec_type == ExecType.FILL.value
    ]
    # exactly one fill -- the closing print
    assert len(fills) == 1
    closing_print_px = fills[0].last_px

    new_orders = [e for e in events if e.msg_type == MsgType.NEW_ORDER_SINGLE.value]
    assert all(closing_print_px >= o.price for o in new_orders)


def test_marking_the_close_fill_after_last_order():
    rng = random.Random(7)
    events, label = marking_the_close(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mtc-3"
    )

    new_orders = [e for e in events if e.msg_type == MsgType.NEW_ORDER_SINGLE.value]
    fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.exec_type == ExecType.FILL.value
    ]
    assert fills[0].transact_time > max(o.transact_time for o in new_orders)


def test_marking_the_close_injected_ids_reference_real_events():
    rng = random.Random(11)
    events, label = marking_the_close(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mtc-4"
    )

    all_cl_ord_ids = {e.cl_ord_id for e in events}
    assert set(label.injected_event_ids) <= all_cl_ord_ids


def test_marking_the_close_scenario_type_tag_on_all_events():
    rng = random.Random(3)
    events, label = marking_the_close(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mtc-5"
    )

    assert all(e.scenario_type == "MARKING_THE_CLOSE" for e in events)
    assert all(e.scenario_id == "sc-mtc-5" for e in events)


def test_marking_the_close_deterministic():
    kwargs = dict(t0=1718500000000, trader_id="t", account="a", symbol="TD",
                  exchange="TSX", mid_price=80.0, scenario_id="sc-det")
    a, _ = marking_the_close(random.Random(1), **kwargs)
    b, _ = marking_the_close(random.Random(1), **kwargs)
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]


def test_marking_the_close_custom_waves():
    rng = random.Random(55)
    events, label = marking_the_close(
        rng, 1718500000000, "trader-9", "ACC-9", "TD", "TSX", 80.0, "sc-mtc-6", waves=5
    )

    new_orders = [e for e in events if e.msg_type == MsgType.NEW_ORDER_SINGLE.value]
    assert len(new_orders) == 5

    # window_start and window_end are ordered
    assert label.window_start < label.window_end
