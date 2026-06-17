"""Training-data builder for the abuse scorer.

Generates a labeled stream, then computes per-(trader, instrument, window) features with a
pure-pandas mirror of pipeline/transforms/gold.py (so ML iterates fast without a Spark JVM).
The formulas match the PySpark gold layer; a consistency check against it lives in tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from synthfix.engine import generate_stream

FEATURES = [
    "n_orders", "n_cancels", "n_execs", "buy_qty", "sell_qty", "distinct_prices",
    "cancel_ratio", "order_to_trade_ratio", "qty_imbalance", "price_move_bps",
    "round_trip_gain_bps", "secs_to_close",
]

_DAY_MS = 86_400_000
_CLOSE_MS_OF_DAY = 57_600_000
_KIND = {"D": "NEW", "8": "EXEC", "F": "CANCEL", "G": "REPLACE"}


def gold_features(events, window_ms: int = 60_000) -> pd.DataFrame:
    df = pd.DataFrame([e.to_dict() for e in events])
    for col in ("price", "last_qty", "last_px"):
        if col not in df:
            df[col] = np.nan
    df["event_kind"] = df["msg_type"].map(_KIND).fillna("OTHER")
    df["is_buy"] = df["side"] == "1"
    df["window_start"] = (df["transact_time"] // window_ms) * window_ms
    df["secs_to_close"] = (_CLOSE_MS_OF_DAY - (df["transact_time"] % _DAY_MS)) / 1000.0

    out = []
    for (trader, sym, ws), g in df.groupby(["trader_id", "symbol", "window_start"]):
        new = g[g.event_kind == "NEW"]
        execs = g[g.event_kind == "EXEC"]
        n_orders, n_cancels, n_execs = len(new), int((g.event_kind == "CANCEL").sum()), len(execs)
        buy_qty = float(new[new.is_buy]["order_qty"].sum())
        sell_qty = float(new[~new.is_buy]["order_qty"].sum())
        priced = g[g["price"].notna()].sort_values("transact_time")
        first_px = float(priced["price"].iloc[0]) if len(priced) else 0.0
        last_px = float(priced["price"].iloc[-1]) if len(priced) else 0.0

        be, se = execs[execs.is_buy], execs[~execs.is_buy]
        buy_vwap = float((be.last_qty * be.last_px).sum() / be.last_qty.sum()) if be.last_qty.sum() > 0 else 0.0
        sell_vwap = float((se.last_qty * se.last_px).sum() / se.last_qty.sum()) if se.last_qty.sum() > 0 else 0.0

        out.append({
            "trader_id": trader, "symbol": sym, "window_start": int(ws),
            "n_orders": n_orders, "n_cancels": n_cancels, "n_execs": n_execs,
            "buy_qty": buy_qty, "sell_qty": sell_qty,
            "distinct_prices": int(priced["price"].nunique()),
            "cancel_ratio": n_cancels / max(n_orders, 1),
            "order_to_trade_ratio": n_orders / max(n_execs, 1),
            "qty_imbalance": (buy_qty - sell_qty) / max(buy_qty + sell_qty, 1.0),
            "price_move_bps": (last_px - first_px) / first_px * 10000.0 if first_px > 0 else 0.0,
            "round_trip_gain_bps": (sell_vwap - buy_vwap) / buy_vwap * 10000.0 if buy_vwap > 0 and sell_vwap > 0 else 0.0,
            "secs_to_close": float(g["secs_to_close"].min()),
        })
    return pd.DataFrame(out)


def build_dataset(seed: int = 0, n_normal: int = 1500, abuse_count: int = 40, window_ms: int = 60_000):
    """Return (X features, y labels 0/1, full gold frame). A window is positive if it overlaps
    an injected scenario's (trader, instrument, window)."""
    events, labels = generate_stream(seed=seed, n_normal=n_normal, abuse_count=abuse_count)
    gf = gold_features(events, window_ms)

    abuse_keys = set()
    for lab in labels:
        w = (lab.window_start // window_ms) * window_ms
        end = (lab.window_end // window_ms) * window_ms
        while w <= end:
            abuse_keys.add((lab.trader_id, lab.instrument, w))
            w += window_ms

    y = np.array(
        [1 if (r.trader_id, r.symbol, r.window_start) in abuse_keys else 0 for r in gf.itertuples()],
        dtype=int,
    )
    X = gf[FEATURES].astype(float).reset_index(drop=True)
    return X, y, gf
