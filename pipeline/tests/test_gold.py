import random

from synthfix.scenarios import spoofing, wash_trade

from pipeline.transforms.bronze import to_bronze
from pipeline.transforms.gold import to_gold
from pipeline.transforms.silver import to_silver


def _gold_for(spark, scenario_fn, sid):
    events, _ = scenario_fn(
        random.Random(1), 1_718_500_000_000, "A-001", "ACC-A-001", "RY", "TSX", 140.0, sid
    )
    raw = [e.to_dict() for e in events]
    return to_gold(to_silver(to_bronze(spark, raw)))


def test_gold_flags_high_cancel_ratio_for_spoofing(spark):
    gold = _gold_for(spark, spoofing, "sc-spoof")
    rows = gold.filter((gold.trader_id == "A-001") & (gold.symbol == "RY")).collect()
    assert rows, "expected a gold feature row for the abusive trader/instrument"
    win = max(rows, key=lambda r: r["n_cancels"])
    # spoofing emits 4 layered BUYs + 1 genuine SELL (5 NEW) and cancels the 4 BUYs
    assert win["n_orders"] == 5
    assert win["n_cancels"] == 4
    assert abs(win["cancel_ratio"] - 0.8) < 1e-6


def test_gold_wash_trade_has_balanced_qty_and_low_cancels(spark):
    gold = _gold_for(spark, wash_trade, "sc-wash")
    win = gold.filter((gold.trader_id == "A-001") & (gold.symbol == "RY")).collect()[0]
    # equal BUY and SELL quantity in the same window => imbalance ~ 0, no cancels
    assert win["n_cancels"] == 0
    assert abs(win["qty_imbalance"]) < 1e-6
