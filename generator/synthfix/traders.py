"""Trader pool: benign traders generate background flow; a small set of abusive traders
are the injection targets for the labeled scenarios."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Trader:
    trader_id: str
    account: str
    abusive: bool


NORMAL_TRADERS: list[Trader] = [
    Trader(f"T-{i:03d}", f"ACC-T-{i:03d}", False) for i in range(20)
]
ABUSIVE_TRADERS: list[Trader] = [
    Trader(f"A-{i:03d}", f"ACC-A-{i:03d}", True) for i in range(5)
]
