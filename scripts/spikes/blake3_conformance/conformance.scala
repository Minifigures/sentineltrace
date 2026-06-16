// P0 spike: Scala side of cross-language audit-hash conformance. Implements the SAME
// frozen byte-grammar as pipeline/shared/audit/audit_chain.py. Run: scala conformance.scala
// Separators built from char codes so the source stays plain ASCII (no control chars).
import java.security.MessageDigest
import java.util.Locale

val US = 0x1f.toChar.toString // unit separator between fields
val RS = 0x1e.toChar.toString // record separator between list elements
val NUL = 0x00.toChar.toString // null sentinel

def cf(v: Any): String = v match {
  case null       => NUL
  case b: Boolean => if (b) "1" else "0"
  case i: Int     => i.toString
  case l: Long    => l.toString
  case d: Double  => String.format(Locale.US, "%.8f", Double.box(d))
  case s: String  => s
  case xs: Seq[_] => xs.map(cf).mkString(RS)
  case other      => throw new RuntimeException("non-canonicalizable: " + other)
}

def canon(fields: Seq[Any]): Array[Byte] =
  fields.map(cf).mkString(US).getBytes("UTF-8")

def hex(bytes: Array[Byte]): String = bytes.map(x => f"${x & 0xff}%02x").mkString

val sample: Seq[Any] = Seq(
  "SPOOFING", "trader-7", "RY", 1718500000000L, 1718500060000L, 4, 0.875, null,
  Seq("e1", "e2", "e3"), Seq("UMIR-2.2"), "equity", 1718500061000L
)

@main def run(): Unit = {
  val b = canon(sample)
  println("BYTES_HEX=" + hex(b))
  println("SHA256=" + hex(MessageDigest.getInstance("SHA-256").digest(b)))
}
