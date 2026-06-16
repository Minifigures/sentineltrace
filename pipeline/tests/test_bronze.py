from pipeline.transforms.bronze import bronze_quarantine, to_bronze


def _order(**over):
    base = {
        "msg_type": "D", "cl_ord_id": "o1", "trader_id": "T-001", "account": "ACC-1",
        "symbol": "RY", "side": "1", "order_qty": 100, "ord_type": "2",
        "transact_time": 1, "exchange_id": "TSX", "price": 140.0,
    }
    base.update(over)
    return base


def test_bronze_keeps_valid_and_adds_metadata(spark):
    df = to_bronze(spark, [_order()], ingest_ts=999, source="test")
    rows = df.collect()
    assert len(rows) == 1
    r = rows[0]
    assert r["cl_ord_id"] == "o1"
    assert r["_ingest_ts"] == 999 and r["_source"] == "test"
    # heterogeneous FIX tags are present as columns even when null for this msg type
    assert "exec_type" in df.columns and r["exec_type"] is None


def test_bronze_quarantines_rows_missing_required_fields(spark):
    raw = [_order(cl_ord_id="good"), _order(cl_ord_id="bad", symbol=None)]
    clean = to_bronze(spark, raw)
    quarantined = bronze_quarantine(spark, raw)
    assert [r["cl_ord_id"] for r in clean.collect()] == ["good"]
    assert [r["cl_ord_id"] for r in quarantined.collect()] == ["bad"]


def test_bronze_handles_mixed_message_types(spark):
    execution = {
        "msg_type": "8", "cl_ord_id": "o1", "trader_id": "T-001", "account": "ACC-1",
        "symbol": "RY", "side": "1", "order_qty": 100, "ord_type": "2",
        "transact_time": 2, "exchange_id": "TSX", "exec_type": "2",
        "last_qty": 100, "last_px": 140.0,
    }
    df = to_bronze(spark, [_order(), execution])
    assert df.count() == 2
    fill = df.filter(df.msg_type == "8").collect()[0]
    assert fill["exec_type"] == "2" and fill["last_px"] == 140.0
