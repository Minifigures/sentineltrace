"""Instrument universe for the synthetic market (equities; derivatives added later)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    exchange: str
    mid: float  # reference mid price
    tick: float


INSTRUMENTS: list[Instrument] = [
    Instrument("RY", "TSX", 140.0, 0.01),
    Instrument("TD", "TSX", 80.0, 0.01),
    Instrument("BNS", "TSX", 65.0, 0.01),
    Instrument("BMO", "TSX", 125.0, 0.01),
    Instrument("CM", "TSX", 60.0, 0.01),
    Instrument("XIU", "TSX", 33.0, 0.01),
]
