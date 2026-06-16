import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    s = (
        SparkSession.builder.appName("sentineltrace-pipeline-tests")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield s
    s.stop()
