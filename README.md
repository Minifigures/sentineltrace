# SentinelTrace

**Explainable trade-surveillance platform.** Synthetic FIX 4.4 order/execution flow streams through a governed lakehouse medallion; stateful Scala detectors flag market-abuse patterns (spoofing/layering, wash trading, front-running, momentum ignition, marking-the-close); a calibrated, SHAP-explained model scores each alert; and an AI agent drafts a regulation-cited Suspicious Trading Report (STR), gated by a closed-world citation check and a CI hallucination gate. Every step is recorded in a tamper-evident hash chain.

> Paste a FIX message, watch it get classified, see the SHAP waterfall, the violated UMIR/MiFID rule, and the auto-drafted STR on one screen, backed by a verifiable audit badge.

## Why it is built this way

Regulated trade surveillance needs AI that is **useful, explainable, and auditable**. SentinelTrace keeps a deterministic rule score authoritative (reproducible with no model in the loop), reports ML score + SHAP + conformal confidence alongside it, grounds every regulatory citation in a governed corpus, and makes every decision replayable through a single audit chain.

## Architecture (high level)

```
FIX generator -> Kafka/Event Hubs -> medallion (bronze/silver/gold)
   -> Scala stateful detectors -> canonical Alert
   -> ML scoring + SHAP -> governance (lineage, RLS, PII masking)
   -> AI agent drafts regulation-cited STR -> eval gate (CI)
   -> web console (one-screen demo)
```

## Repository layout

| Path | Purpose |
|---|---|
| `generator/` | Synthetic FIX 4.4 generator with labeled abuse scenarios |
| `pipeline/` | Medallion transforms + the canonical contract + shared audit chain |
| `scala-detectors/` | Stateful market-abuse detectors (Scala, sbt) |
| `ml/` | Scoring, calibration, SHAP, conformal prediction |
| `agent/` | STR drafting agent (tools, grounding, safety) |
| `evals/` | Eval harness + quality gate |
| `web/` | Next.js surveillance console |
| `infra/` | Terraform + Bicep + Databricks Asset Bundles |
| `tests/` | Cross-language contract + integration tests |

## Status

Early development. Built local-first (Docker) before any cloud deployment.

## License

MIT
