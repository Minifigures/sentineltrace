import random

from synthfix.fix import ExecType, MsgType, Side
from synthfix.scenarios import spoofing, wash_trade


def test_spoofing_pattern_is_well_formed():
    rng = random.Random(42)
    events, label = spoofing(rng, 1718500000000, "trader-7", "ACC-7", "RY", "TSX", 100.0, "sc-spoof-1")

    assert label.abuse_type == "SPOOFING"
    assert label.trader_id == "trader-7" and label.instrument == "RY"

    # large passive BUY layer
    buys = [e for e in events if e.msg_type == MsgType.NEW_ORDER_SINGLE.value and e.side == Side.BUY.value]
    assert len(buys) >= 4
    assert all(b.order_qty >= 5000 for b in buys)

    # every spoof BUY is subsequently cancelled
    cancels = [e for e in events if e.msg_type == MsgType.ORDER_CANCEL_REQUEST.value]
    cancelled_origs = {c.orig_cl_ord_id for c in cancels}
    assert {b.cl_ord_id for b in buys} <= cancelled_origs

    # a genuine opposite-side SELL gets filled before the cancels (the point of the spoof)
    sell_fills = [
        e for e in events
        if e.msg_type == MsgType.EXECUTION_REPORT.value
        and e.side == Side.SELL.value
        and e.exec_type == ExecType.FILL.value
    ]
    assert len(sell_fills) == 1
    assert sell_fills[0].transact_time < min(c.transact_time for c in cancels)

    # ground-truth ids all reference real events
    all_ids = {e.cl_ord_id for e in events}
    assert set(label.injected_event_ids) <= all_ids


def test_wash_trade_is_self_matching_same_trader():
    rng = random.Random(7)
    events, label = wash_trade(rng, 1718500000000, "trader-3", "ACC-3", "BNS", "TSX", 50.0, "sc-wash-1")

    assert label.abuse_type == "WASH_TRADE"
    # one trader on BOTH sides
    assert all(e.trader_id == "trader-3" for e in events)
    news = [e for e in events if e.msg_type == MsgType.NEW_ORDER_SINGLE.value]
    assert {e.side for e in news} == {Side.BUY.value, Side.SELL.value}

    # identical price and quantity => no change in beneficial ownership (wash)
    assert len({e.price for e in news}) == 1
    assert len({e.order_qty for e in news}) == 1

    # both sides fill in the same tight instant
    fills = [e for e in events if e.msg_type == MsgType.EXECUTION_REPORT.value]
    assert len(fills) == 2
    assert len({f.transact_time for f in fills}) == 1


def test_scenarios_are_deterministic():
    a, _ = spoofing(random.Random(1), 1000, "t", "a", "RY", "TSX", 10.0, "s1")
    b, _ = spoofing(random.Random(1), 1000, "t", "a", "RY", "TSX", 10.0, "s1")
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]
