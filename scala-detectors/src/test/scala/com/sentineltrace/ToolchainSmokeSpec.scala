package com.sentineltrace

import org.apache.spark.sql.SparkSession
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** P0 spike: prove the locked interop triple actually runs before P4 commits to it.
  * JDK 17 (Temurin) + Scala 2.13.16 + Spark 4.0.0 + Delta 4.0.0, local mode. */
class ToolchainSmokeSpec extends AnyFlatSpec with Matchers {

  "the toolchain" should "run a local Spark 4.0 job on JDK 17 / Scala 2.13.16" in {
    val spark = SparkSession
      .builder()
      .appName("toolchain-smoke")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2")
      .getOrCreate()
    try {
      import spark.implicits._
      val df = Seq(("RY", 3), ("RY", 5), ("BNS", 2)).toDF("instrument", "qty")
      val totals =
        df.groupBy("instrument").sum("qty").as[(String, Long)].collect().toMap
      totals("RY") shouldBe 8L
      totals("BNS") shouldBe 2L
    } finally spark.stop()
  }
}
