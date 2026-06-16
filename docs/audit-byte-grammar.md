# Audit-hash byte grammar (cross-language, frozen)

The audit chain links every decision into a tamper-evident sequence. For the chain to
verify identically in Python, Scala (JVM), and TypeScript, the bytes that get hashed
must be produced by this exact grammar in all three languages. **Never use a language's
native JSON serializer for the hashed bytes** (key ordering, whitespace, float and
timestamp formatting all differ by default and silently break conformance).

## Hash algorithm

Default **SHA-256** (present in every standard library; zero dependency; trivially
identical across languages). BLAKE3 is an opt-in upgrade, enabled only once the
tri-language byte-conformance spike is green. The chosen algorithm is recorded with the
chain so verification is unambiguous.

## Field rendering

Each field renders to a string:

| Type | Rendering |
|---|---|
| null / None | the single byte `0x00` (NUL) |
| bool | `1` (true) or `0` (false) |
| int | base-10 digits, no separators, leading `-` if negative |
| float | exactly 8 decimal places, fixed-point, no exponent (e.g. `0.73000000`) |
| string | the raw UTF-8 string (no quoting, no escaping) |
| list | elements rendered recursively, joined by RS = `0x1e` |

## Record assembly

1. Take the field values in their **contract-fixed order** (for an Alert, that is
   `ALERT_HASH_FIELD_ORDER` in `alert_contract.py`).
2. Render each field per the table above.
3. Join the rendered fields with US = `0x1f`.
4. Encode the joined string as **UTF-8**. No surrounding whitespace, ever.

## Chain link

```
entry_hash = H( prev_hash_ascii + "|" + canonical_bytes(entry) )
genesis prev_hash = "0" * 64
```

## Conformance fixtures

`scripts/spikes/blake3_conformance/` holds golden **input bytes** (hex) and golden
**digests** for a fixed sample record. The Python, Scala, and TS serializers must each
reproduce the golden input bytes (so a mismatch shows as a byte diff, not just a hash
diff) and the golden digest. CI runs this in all three languages.

## Floats

Floats in the hashed payload are limited to scores in `[0,1]` rendered at 8 decimals.
Avoid hashing raw market prices; if ever needed, render as integer minor units, not
floats.
