from pipeline.transforms.bronze import to_bronze
from pipeline.transforms.silver import to_silver


def _ev(**over):
    base = {
        "msg_type": "D", "cl_ord_id": "o1", "trader_id": "T-001", "account": "ACC-1",
        "symbol": "RY", "side": "1", "order_qty": 100, "ord_type": "2",
        "transact_time": 1, "exchange_id": "TSX", "price": 140.0,
    }
    base.update(over)
    return base


def test_silver_derives_event_kind_and_dedups(spark):
    raw = [
        _ev(cl_ord_id="o1"),
        _ev(cl_ord_id="o1"),  # exact duplicate -> dropped
        _ev(cl_ord_id="c1", msg_type="F", side="1", transact_time=2),
        _ev(cl_ord_id="s1", side="2", transact_time=3),
    ]
    s = to_silver(to_bronze(spark, raw))
    assert s.count() == 3  # one dup removed
    rows = {r["cl_ord_id"]: r for r in s.collect()}
    assert rows["o1"]["event_kind"] == "NEW"
    assert rows["c1"]["event_kind"] == "CANCEL"
    assert rows["o1"]["is_buy"] is True
    assert rows["s1"]["is_buy"] is False
    assert rows["o1"]["desk"] == "equity" and rows["o1"]["asset_class"] == "equity"
    assert abs(rows["o1"]["notional"] - 14000.0) < 1e-6
