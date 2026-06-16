package com.sentineltrace

import com.sentineltrace.detectors.Spoofing
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class SpoofingSpec extends AnyFlatSpec with Matchers {

  private def gf(cancelRatio: Double, nOrders: Long, ott: Double): GoldFeatures =
    GoldFeatures(
      traderId = "A-001", instrument = "RY", windowStart = 0L, windowEnd = 60000L,
      desk = "equity", assetClass = "equity",
      nOrders = nOrders, nCancels = math.round(cancelRatio * nOrders), nExecs = 1L,
      buyQty = 5000L, sellQty = 200L, distinctPrices = 4L,
      cancelRatio = cancelRatio, orderToTradeRatio = ott, qtyImbalance = 0.9
    )

  "Spoofing.score" should "be high for a layered place-and-cancel pattern" in {
    val s = Spoofing.score(gf(0.8, 5, 5.0))
    s should be > 0.5
    Severity.fromRuleScore(s) shouldBe 4
  }

  it should "be zero below the minimum order count" in {
    Spoofing.score(gf(1.0, 2, 1.0)) shouldBe 0.0
  }

  "Spoofing.detect" should "emit a SPOOFING alert with regulation refs and a 64-hex audit hash" in {
    val a = Spoofing.detect(gf(0.8, 5, 5.0), createdAt = 123L)
    a shouldBe defined
    a.get.detector shouldBe "SPOOFING"
    a.get.severity shouldBe 4
    a.get.regulationRefs should contain("UMIR_2.2")
    a.get.auditHash.length shouldBe 64
    a.get.mlScore shouldBe None
  }

  it should "not emit for benign flow" in {
    Spoofing.detect(gf(0.1, 10, 1.0), 0L) shouldBe None
  }

  it should "produce a deterministic alert id independent of createdAt" in {
    val a1 = Spoofing.detect(gf(0.8, 5, 5.0), 1L).get
    val a2 = Spoofing.detect(gf(0.8, 5, 5.0), 2L).get
    a1.alertId shouldBe a2.alertId
  }
}
