// P0 spike: JS/TS side of cross-language audit-hash conformance. Same frozen byte-grammar
// as pipeline/shared/audit/audit_chain.py. Run: node conformance.mjs
// Separators from char codes so the source stays plain ASCII.
import crypto from "node:crypto";

const US = String.fromCharCode(0x1f); // unit separator between fields
const RS = String.fromCharCode(0x1e); // record separator between list elements
const NUL = String.fromCharCode(0x00); // null sentinel

function cf(v) {
  if (v === null) return NUL;
  if (typeof v === "boolean") return v ? "1" : "0";
  if (typeof v === "bigint") return v.toString();
  if (typeof v === "number") return Number.isInteger(v) ? v.toString() : v.toFixed(8);
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v.map(cf).join(RS);
  throw new Error("non-canonicalizable: " + v);
}

function canon(fields) {
  return Buffer.from(fields.map(cf).join(US), "utf-8");
}

const sample = [
  "SPOOFING", "trader-7", "RY", 1718500000000, 1718500060000, 4, 0.875, null,
  ["e1", "e2", "e3"], ["UMIR-2.2"], "equity", 1718500061000,
];

const b = canon(sample);
console.log("BYTES_HEX=" + b.toString("hex"));
console.log("SHA256=" + crypto.createHash("sha256").update(b).digest("hex"));
