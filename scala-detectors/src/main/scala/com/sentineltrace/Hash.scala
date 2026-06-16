package com.sentineltrace

import java.security.MessageDigest
import java.util.Locale

/** Audit-hash byte grammar — the Scala mirror of pipeline/shared/audit/audit_chain.py and
  * docs/audit-byte-grammar.md. Proven byte-identical to Python and JS in the P0 conformance
  * spike, so detector-emitted audit hashes verify in the same chain as every other subsystem. */
object Hash {
  private val US = 0x1f.toChar.toString // unit separator between fields
  private val RS = 0x1e.toChar.toString // record separator between list elements
  private val NUL = 0x00.toChar.toString // null sentinel

  def canonicalField(v: Any): String = v match {
    case null            => NUL
    case b: Boolean      => if (b) "1" else "0"
    case i: Int          => i.toString
    case l: Long         => l.toString
    case d: Double       => String.format(Locale.US, "%.8f", Double.box(d))
    case s: String       => s
    case None            => NUL
    case Some(x)         => canonicalField(x)
    case xs: Seq[_]      => xs.map(canonicalField).mkString(RS)
    case other           => throw new RuntimeException("non-canonicalizable: " + other)
  }

  def canonicalBytes(fields: Seq[Any]): Array[Byte] =
    fields.map(canonicalField).mkString(US).getBytes("UTF-8")

  def sha256Hex(bytes: Array[Byte]): String =
    MessageDigest.getInstance("SHA-256").digest(bytes).map(b => f"${b & 0xff}%02x").mkString
}
