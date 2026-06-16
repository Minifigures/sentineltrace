"""Ground-truth label sidecar. Writes ScenarioLabels to JSONL (the Delta/Parquet sidecar
in ADLS/MinIO is wired in the pipeline phase; JSONL keeps the generator dependency-free)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .scenarios import ScenarioLabel


def write_labels_jsonl(labels: list[ScenarioLabel], path: str | Path) -> int:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        for label in labels:
            f.write(json.dumps(asdict(label), separators=(",", ":")) + "\n")
    return len(labels)
