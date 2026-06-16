"""Unified, tamper-evident audit chain — the single library every Python subsystem
calls (generator, pipeline, ml, agent, governance). A Scala mirror exists for the
detector. Per-subsystem audit tables are VIEWS over the one chain.

Design decisions (de-risked up front):
- Hash algorithm is PLUGGABLE. Default is SHA-256 (in every stdlib, byte-identical
  across Python/JVM/TS with zero deps) so the audit badge is never blocked. BLAKE3 is
  an opt-in upgrade once tri-language byte-conformance is proven (see scripts/spikes).
- The HASHED BYTES are produced by a hand-written, language-agnostic byte grammar
  (NEVER language-native JSON), specified in docs/audit-byte-grammar.md. This is the
  only way Python == Scala == TS digests are guaranteed identical.
- The chain is a linked hash: entry.hash = H(prev_hash || canonical_bytes(entry)).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

GENESIS_HASH = "0" * 64  # SHA-256 hex width; first entry links to this

try:  # optional acceleration; SHA-256 remains the cross-language default
    import blake3 as _blake3  # type: ignore

    _HAS_BLAKE3 = True
except Exception:  # pragma: no cover
    _HAS_BLAKE3 = False


def _digest(data: bytes, algo: str) -> str:
    if algo == "sha256":
        return hashlib.sha256(data).hexdigest()
    if algo == "blake3":
        if not _HAS_BLAKE3:
            raise RuntimeError("blake3 not installed; use algo='sha256'")
        return _blake3.blake3(data).hexdigest()  # type: ignore
    raise ValueError(f"unsupported algo: {algo}")


def canonical_field(value: object) -> str:
    """Render ONE field to its canonical string per the byte grammar.

    Rules (see docs/audit-byte-grammar.md):
      - None        -> "\\x00" (NUL sentinel)
      - bool        -> "1" / "0"
      - int         -> base-10, no separators
      - float       -> fixed 8-decimal places, no exponent, no trailing strip
      - str         -> the raw UTF-8 string
      - list        -> elements joined by RS (\\x1e), recursively canonicalized
    """
    if value is None:
        return "\x00"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.8f}"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\x1e".join(canonical_field(v) for v in value)
    raise TypeError(f"non-canonicalizable field type: {type(value)}")


def canonical_bytes(ordered_fields: list[object]) -> bytes:
    """Join ordered fields with US (\\x1f) and encode UTF-8. Field ORDER is fixed by
    the caller's contract (e.g. ALERT_HASH_FIELD_ORDER). No whitespace, ever."""
    return "\x1f".join(canonical_field(f) for f in ordered_fields).encode("utf-8")


@dataclass
class AuditEntry:
    subsystem: str  # "generator" | "pipeline" | "detector" | "ml" | "agent" | "governance"
    action: str  # e.g. "ML_SCORED", "STR_DRAFTED", "TABLE_WRITTEN"
    ref_id: str  # alert_id / event_id / run_id this entry is about
    payload_fields: list[object]  # ordered, canonicalizable summary of what happened
    ts: int  # epoch millis
    prev_hash: str = GENESIS_HASH
    entry_hash: str = ""

    def compute(self, algo: str = "sha256") -> "AuditEntry":
        body = canonical_bytes(
            [self.subsystem, self.action, self.ref_id, self.ts, *self.payload_fields]
        )
        self.entry_hash = _digest(self.prev_hash.encode("ascii") + b"|" + body, algo)
        return self


@dataclass
class AuditChainWriter:
    """Append-only in-memory chain head; persisted to gold.audit_chain in the lakehouse.
    Merkle anchoring (every N entries) is added in the hardening phase for O(log N) proofs."""

    algo: str = "sha256"
    head: str = GENESIS_HASH
    entries: list[AuditEntry] = field(default_factory=list)

    def append(self, subsystem: str, action: str, ref_id: str, payload_fields: list[object], ts: int) -> AuditEntry:
        e = AuditEntry(subsystem, action, ref_id, payload_fields, ts, prev_hash=self.head).compute(self.algo)
        self.head = e.entry_hash
        self.entries.append(e)
        return e

    def verify(self) -> bool:
        prev = GENESIS_HASH
        for e in self.entries:
            recomputed = AuditEntry(
                e.subsystem, e.action, e.ref_id, e.payload_fields, e.ts, prev_hash=prev
            ).compute(self.algo)
            if recomputed.entry_hash != e.entry_hash:
                return False
            prev = e.entry_hash
        return True
