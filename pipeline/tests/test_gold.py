import random

from synthfix.scenarios import front_running, momentum_ignition, spoofing, wash_trade

from pipeline.transforms.bronze import to_bronze
from pipeline.transforms.gold import to_gold
from pipeline.transforms.silver import to_silver


def _gold_for(spark, scenario_fn, sid):
    events, _ = scenario_fn(
        random.Random(1), 1_718_500_000_000, "A-001", "ACC-A-001", "RY", "TSX", 140.0, sid
    )
    raw = [e.to_dict() for e in events]
    return to_gold(to_silver(to_bronze(spark, raw)))


def _abuser_window(spark, scenario_fn, sid):
    gold = _gold_for(spark, scenario_fn, sid)
    rows = gold.filter((gold.trader_id == "A-001") & (gold.symbol == "RY")).collect()
    assert rows, "expected a gold row for the abusive trader"
    return max(rows, key=lambda r: r["n_orders"] + r["n_execs"])


def test_gold_flags_high_cancel_ratio_for_spoofing(spark):
    win = _abuser_window(spark, spoofing, "sc-spoof")
    assert win["n_orders"] == 5
    assert win["n_cancels"] == 4
    assert abs(win["cancel_ratio"] - 0.8) < 1e-6


def test_gold_wash_trade_balanced_with_zero_round_trip_gain(spark):
    win = _abuser_window(spark, wash_trade, "sc-wash")
    assert win["n_cancels"] == 0
    assert abs(win["qty_imbalance"]) < 1e-6
    # same price both sides => no realized gain (this is what separates wash from front-running)
    assert abs(win["round_trip_gain_bps"]) < 1e-6


def test_gold_momentum_shows_upward_price_move_and_heavy_fills(spark):
    win = _abuser_window(spark, momentum_ignition, "sc-mom")
    assert win["price_move_bps"] > 0  # price walked up across the burst
    assert win["n_execs"] >= 5  # aggressive fills, not cancels
    assert win["n_cancels"] == 0


def test_gold_front_running_has_positive_round_trip_gain(spark):
    win = _abuser_window(spark, front_running, "sc-fr")
    # abuser bought low then sold high in the same window => realized gain
    assert win["round_trip_gain_bps"] > 0
    assert abs(win["qty_imbalance"]) < 1e-6  # balanced round trip
