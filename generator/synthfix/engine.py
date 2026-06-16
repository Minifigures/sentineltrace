"""Stream engine: interleaves benign background order flow with injected, labeled
market-abuse scenarios so detectors face realistic noise. Deterministic given a seed."""

from __future__ import annotations

import random

from .fix import FixEvent, MsgType, OrdType, Side
from .instruments import INSTRUMENTS
from .scenarios import (
    ScenarioLabel,
    front_running,
    marking_the_close,
    momentum_ignition,
    spoofing,
    wash_trade,
)
from .traders import ABUSIVE_TRADERS, NORMAL_TRADERS

SCENARIO_FNS = {
    "SPOOFING": spoofing,
    "WASH_TRADE": wash_trade,
    "FRONT_RUNNING": front_running,
    "MOMENTUM_IGNITION": momentum_ignition,
    "MARKING_THE_CLOSE": marking_the_close,
}


def _benign_order(rng: random.Random, t: int, seq: int) -> FixEvent:
    trader = rng.choice(NORMAL_TRADERS)
    inst = rng.choice(INSTRUMENTS)
    side = rng.choice([Side.BUY.value, Side.SELL.value])
    qty = rng.randint(1, 20) * 100
    px = round(inst.mid + rng.uniform(-0.05, 0.05), 2)
    return FixEvent(
        MsgType.NEW_ORDER_SINGLE.value, f"n-{seq}", trader.trader_id, trader.account,
        inst.symbol, side, qty, OrdType.LIMIT.value, t, inst.exchange, price=px,
    )  # scenario_type left None => benign


def generate_stream(
    seed: int = 0,
    n_normal: int = 500,
    abuse_count: int = 5,
    t_start: int = 1_718_500_000_000,
    dt_ms: int = 100,
) -> tuple[list[FixEvent], list[ScenarioLabel]]:
    """Produce a time-ordered event stream of `n_normal` benign orders with `abuse_count`
    labeled abuse scenarios injected at random points (cycling through the 5 archetypes)."""
    rng = random.Random(seed)
    events: list[FixEvent] = []
    labels: list[ScenarioLabel] = []

    abuse_count = min(abuse_count, n_normal)
    inject_at = set(rng.sample(range(n_normal), abuse_count))
    archetypes = list(SCENARIO_FNS)

    t = t_start
    injected = 0
    for i in range(n_normal):
        events.append(_benign_order(rng, t, i))
        t += dt_ms
        if i in inject_at:
            atype = archetypes[injected % len(archetypes)]
            injected += 1
            ab = rng.choice(ABUSIVE_TRADERS)
            inst = rng.choice(INSTRUMENTS)
            sid = f"abuse-{atype.lower()}-{injected}"
            evs, lab = SCENARIO_FNS[atype](
                rng, t, ab.trader_id, ab.account, inst.symbol, inst.exchange, inst.mid, sid
            )
            events.extend(evs)
            labels.append(lab)
            t += 2000  # step past the scenario window before resuming benign flow

    events.sort(key=lambda e: e.transact_time)
    return events, labels
