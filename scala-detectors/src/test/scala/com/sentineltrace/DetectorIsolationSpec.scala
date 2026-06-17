package com.sentineltrace

import com.sentineltrace.detectors.{FrontRunning, Momentum, Spoofing, WashTrade}
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** The detection matrix: each of the four window-aggregate detectors must fire on its own
  * archetype window and stay silent on the other three (no false positives). */
class DetectorIsolationSpec extends AnyFlatSpec with Matchers {

  private def base(trader: String): GoldFeatures =
    GoldFeatures(trader, "RY", 0L, 60000L, "equity", "equity",
      0L, 0L, 0L, 0L, 0L, 0L, 0.0, 0.0, 0.0)

  private val spoof = base("A-001").copy(
    nOrders = 5L, nCancels = 4L, nExecs = 1L, buyQty = 20000L, sellQty = 200L,
    distinctPrices = 4L, cancelRatio = 0.8, orderToTradeRatio = 5.0, qtyImbalance = 0.98)

  private val wash = base("A-002").copy(
    nOrders = 2L, nExecs = 2L, buyQty = 1000L, sellQty = 1000L, distinctPrices = 1L,
    orderToTradeRatio = 1.0, qtyImbalance = 0.0, roundTripGainBps = 0.0)

  private val front = base("A-003").copy(
    nOrders = 2L, nExecs = 2L, buyQty = 600L, sellQty = 600L, distinctPrices = 2L,
    orderToTradeRatio = 1.0, qtyImbalance = 0.0,
    buyVwap = 140.0, sellVwap = 140.1, roundTripGainBps = 7.1)

  private val momentum = base("A-004").copy(
    nOrders = 6L, nExecs = 6L, buyQty = 1250L, sellQty = 2000L, distinctPrices = 6L,
    cancelRatio = 0.0, orderToTradeRatio = 1.0, qtyImbalance = -0.23,
    priceMoveBps = 2.9, roundTripGainBps = 1.4)

  private val detectors: Map[String, GoldFeatures => Option[Alert]] = Map(
    "SPOOFING" -> (g => Spoofing.detect(g, 0L)),
    "WASH_TRADE" -> (g => WashTrade.detect(g, 0L)),
    "FRONT_RUNNING" -> (g => FrontRunning.detect(g, 0L)),
    "MOMENTUM_IGNITION" -> (g => Momentum.detect(g, 0L))
  )

  private val windows: Map[String, GoldFeatures] = Map(
    "SPOOFING" -> spoof, "WASH_TRADE" -> wash,
    "FRONT_RUNNING" -> front, "MOMENTUM_IGNITION" -> momentum)

  "each detector" should "fire on its own archetype and stay silent on the other three" in {
    for ((name, detect) <- detectors; (winName, win) <- windows) {
      val res = detect(win)
      if (name == winName) withClue(s"$name should fire on $winName: ") {
        res shouldBe defined
        res.get.detector shouldBe name
      }
      else withClue(s"$name must NOT fire on $winName: ") { res shouldBe None }
    }
  }

  "every archetype" should "reach severity >= 4 (STR-eligible)" in {
    windows.foreach { case (name, win) => detectors(name)(win).get.severity should be >= 4 }
  }
}
