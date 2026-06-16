"""Bronze layer: schema-enforced ingestion of raw FIX events.

Pure-function transform (no streaming, no Docker) so it is unit-testable on local
DataFrames now and lifts unchanged into the DLT bronze node later. Raw FIX event dicts
(as emitted by generator/synthfix FixEvent.to_dict()) -> typed bronze DataFrame with
ingestion metadata; rows missing any required field are quarantined out of the clean set.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from pipeline.conf.schemas import RAW_FIX_SCHEMA, REQUIRED_BRONZE_FIELDS

_FIELD_NAMES = [f.name for f in RAW_FIX_SCHEMA.fields]


def _required_not_null():
    cond = F.lit(True)
    for c in REQUIRED_BRONZE_FIELDS:
        cond = cond & F.col(c).isNotNull()
    return cond


def to_bronze(
    spark: SparkSession,
    raw_events: list[dict],
    ingest_ts: int = 0,
    source: str = "fix.local",
) -> DataFrame:
    """Build the clean bronze DataFrame from raw FIX event dicts. Missing keys become NULL
    (different FIX msg types carry different tags); rows missing a REQUIRED field are dropped."""
    rows = [tuple(ev.get(name) for name in _FIELD_NAMES) for ev in raw_events]
    df = spark.createDataFrame(rows, RAW_FIX_SCHEMA)
    df = (
        df.withColumn("_ingest_ts", F.lit(ingest_ts).cast("long"))
        .withColumn("_source", F.lit(source))
    )
    return df.filter(_required_not_null())


def bronze_quarantine(
    spark: SparkSession, raw_events: list[dict], ingest_ts: int = 0, source: str = "fix.local"
) -> DataFrame:
    """The complement of to_bronze: rows rejected for missing required fields (for DQ metrics)."""
    rows = [tuple(ev.get(name) for name in _FIELD_NAMES) for ev in raw_events]
    df = spark.createDataFrame(rows, RAW_FIX_SCHEMA)
    df = df.withColumn("_ingest_ts", F.lit(ingest_ts).cast("long")).withColumn("_source", F.lit(source))
    return df.filter(~_required_not_null())
