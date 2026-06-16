"""P0 spike: Python side of the cross-language audit-hash conformance check.
Uses the SHIPPING serializer (pipeline/shared/audit/audit_chain.py) so what we prove
is exactly what runs. Scala and JS must reproduce these bytes and this digest."""

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline" / "shared" / "audit"))
from audit_chain import canonical_bytes  # noqa: E402  (shipping serializer)

# A representative record exercising every field type: str, long, int, float, null, list.
SAMPLE = [
    "SPOOFING",
    "trader-7",
    "RY",
    1718500000000,
    1718500060000,
    4,
    0.875,
    None,
    ["e1", "e2", "e3"],
    ["UMIR-2.2"],
    "equity",
    1718500061000,
]

b = canonical_bytes(SAMPLE)
print("BYTES_HEX=" + b.hex())
print("SHA256=" + hashlib.sha256(b).hexdigest())
