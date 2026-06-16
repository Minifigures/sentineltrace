.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help local-up local-down local-seed local-pipeline detectors-local \
        ml-score agent-demo eval-gate local-e2e test contract spikes

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## ---- Local-first stack (sequential by design; 12 GiB WSL budget) ----
local-up: ## Start Docker stack (Redpanda, MinIO, Postgres)   [P2]
	@echo "TODO P2: docker compose up -d redpanda minio postgres"

local-down: ## Stop the Docker stack
	@echo "TODO P2: docker compose down"

local-seed: ## Generate + produce labeled FIX events            [P2]
	@echo "TODO P2: run generator -> Kafka topics + scenario_labels"

local-pipeline: ## Run bronze->silver->gold (Spark 3.5)          [P3]
	@echo "TODO P3: spark35 medallion to MinIO Delta"

detectors-local: ## Run Scala detectors (Spark 4.0, OSS)         [P4]
	@echo "TODO P4: sbt run detectors over gold -> alerts"

ml-score: ## Score + SHAP-explain alerts (local mlruns)          [P5]
	@echo "TODO P5: batch_score fills ml_score + shap_top_features"

agent-demo: ## Draft STR for a sev-5 alert (cassette)            [P6]
	@echo "TODO P6: STR agent via recorded Foundry cassettes"

eval-gate: ## Run eval suite + hallucination gate               [P6]
	@echo "TODO P6: azure-ai-evaluation gate vs thresholds.py"

## ---- The hard gate ----
local-e2e: ## Full local demo, SEQUENTIAL (the M7 gate)          [P7]
	@echo "TODO P7: paste-FIX -> classify -> SHAP -> cite -> STR -> audit verify"

## ---- Quality ----
test: ## Run all tests (pytest + sbt test + web)
	@echo "TODO: pytest && (cd scala-detectors && sbt test) && (cd web && npm test)"

contract: ## Run the cross-language contract-sync test           [P1]
	@echo "TODO P1: assert Pydantic == PySpark == Scala == TS alert shape"

spikes: ## Run the P0 de-risking spikes (transformWithState, BLAKE3)
	@echo "TODO P0: scala-detectors transformWithState spike + tri-language hash conformance"
