package com.sentineltrace

import com.sentineltrace.detectors.{Spoofing, WashTrade}
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class WashTradeSpec extends AnyFlatSpec with Matchers {

  // a balanced, executed, single-price round trip by one trader (wash)
  private val washWindow = GoldFeatures(
    traderId = "A-002", instrument = "RY", windowStart = 0L, windowEnd = 60000L,
    desk = "equity", assetClass = "equity",
    nOrders = 2L, nCancels = 0L, nExecs = 2L, buyQty = 1000L, sellQty = 1000L,
    distinctPrices = 1L, cancelRatio = 0.0, orderToTradeRatio = 1.0, qtyImbalance = 0.0
  )

  // a spoofing-shaped window (one-sided, cancel-heavy, one fill)
  private val spoofWindow = GoldFeatures(
    traderId = "A-001", instrument = "RY", windowStart = 0L, windowEnd = 60000L,
    desk = "equity", assetClass = "equity",
    nOrders = 5L, nCancels = 4L, nExecs = 1L, buyQty = 20000L, sellQty = 200L,
    distinctPrices = 4L, cancelRatio = 0.8, orderToTradeRatio = 5.0, qtyImbalance = 0.98
  )

  "WashTrade.detect" should "fire severity 5 on a balanced self-matched round trip" in {
    val a = WashTrade.detect(washWindow, createdAt = 1L)
    a shouldBe defined
    a.get.detector shouldBe "WASH_TRADE"
    a.get.severity shouldBe 5
    a.get.auditHash.length shouldBe 64
  }

  it should "not fire on a spoofing-shaped (one-sided, single-fill) window" in {
    WashTrade.detect(spoofWindow, 0L) shouldBe None
  }

  "the two detectors" should "not cross-fire on each other's signature window" in {
    // spoofing detector stays quiet on the wash window (too few orders)
    Spoofing.detect(washWindow, 0L) shouldBe None
    // wash detector stays quiet on the spoof window (one-sided, single fill)
    WashTrade.detect(spoofWindow, 0L) shouldBe None
  }
}
