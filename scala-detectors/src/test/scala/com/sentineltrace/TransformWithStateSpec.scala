package com.sentineltrace

import java.nio.file.Files

import org.apache.spark.sql.{Dataset, Encoders, SparkSession}
import org.apache.spark.sql.execution.streaming.MemoryStream
import org.apache.spark.sql.streaming.{OutputMode, StatefulProcessor, TimeMode, TimerValues, TTLConfig, ValueState}
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Top-level so Spark can derive an Encoder. */
case class Order(instrument: String, qty: Long)

/** P0 spike: the EXACT API the five detectors use. A per-key running total kept in
  * ValueState across micro-batches — proves transformWithState + state persistence +
  * the typed-state handle on Spark 4.0 before P4 builds five real processors on it. */
class RunningQtyProcessor extends StatefulProcessor[String, Order, (String, Long)] {
  @transient private var total: ValueState[Long] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    total = getHandle.getValueState[Long]("total", Encoders.scalaLong, TTLConfig.NONE)

  override def handleInputRows(
      key: String,
      inputRows: Iterator[Order],
      timerValues: TimerValues
  ): Iterator[(String, Long)] = {
    var sum = if (total.exists()) total.get() else 0L
    inputRows.foreach(o => sum += o.qty)
    total.update(sum)
    Iterator((key, sum))
  }

  override def close(): Unit = ()
}

class TransformWithStateSpec extends AnyFlatSpec with Matchers {

  "transformWithState" should "accumulate per-key ValueState across micro-batches" in {
    val spark = SparkSession
      .builder()
      .appName("tws-spike")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2")
      // transformWithState uses multiple state column families -> RocksDB store is REQUIRED
      // (the default HDFSBackedStateStoreProvider rejects it). This is also optimization O1.
      .config(
        "spark.sql.streaming.stateStore.providerClass",
        "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider"
      )
      .getOrCreate()

    import spark.implicits._
    implicit val sqlCtx = spark.sqlContext
    val ckpt = Files.createTempDirectory("tws-ckpt").toString

    val input = MemoryStream[Order]
    val result: Dataset[(String, Long)] =
      input
        .toDS()
        .groupByKey(_.instrument)
        .transformWithState(new RunningQtyProcessor(), TimeMode.None(), OutputMode.Update())

    val query = result
      .toDF("instrument", "running")
      .writeStream
      .format("memory")
      .queryName("tws_out")
      .outputMode("update")
      .option("checkpointLocation", ckpt)
      .start()

    try {
      input.addData(Order("RY", 3), Order("RY", 5), Order("BNS", 2))
      query.processAllAvailable()
      input.addData(Order("RY", 10))
      query.processAllAvailable()

      val emitted = spark.table("tws_out").as[(String, Long)].collect()
      val latest = emitted.groupBy(_._1).map { case (k, vs) => k -> vs.map(_._2).max }

      latest("RY") shouldBe 18L // 3 + 5, then carried forward + 10
      latest("BNS") shouldBe 2L
    } finally {
      query.stop()
      spark.stop()
    }
  }
}
