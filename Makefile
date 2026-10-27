# Single entry point for common tasks. Run `make help` to list them.

API := uv --directory apps/api
WEB := pnpm --dir apps/web

.DEFAULT_GOAL := help
.PHONY: help docs-check services-up services-down api-install api-dev api-format api-check \
	data-hotpotqa data-synthetic eval-retrieval eval-chunking eval-answers eval-cross-check eval-report eval-models eval-prompts load-test web-install web-dev web-format web-check

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-17s %s\n", $$1, $$2}'

docs-check: ## Fail if the docs name a path, make target or ADR that doesn't exist
	$(API) run python $(CURDIR)/scripts/check_docs.py

services-up: ## Start local Postgres (:5440) and Qdrant (:6333), wait until healthy
	docker compose up -d --wait

services-down: ## Stop local services (data is kept in Docker volumes)
	docker compose down

api-install: ## Install backend dependencies
	$(API) sync

api-dev: ## Run the backend with auto-reload on :8000
	$(API) run uvicorn --factory investigation_engine.main:create_app --reload

api-format: ## Auto-format and auto-fix backend code
	$(API) run ruff format .
	$(API) run ruff check --fix .

api-check: ## Run all backend quality gates (same as CI)
	$(API) run ruff check .
	$(API) run ruff format --check .
	$(API) run mypy src tests
	$(API) run pytest -q

data-hotpotqa: ## Index the HotpotQA corpus (66k docs, resumable) into the .env services
	$(API) run python -m investigation_engine.datasets.hotpotqa

data-synthetic: ## Index the synthetic Northwind Pay corpus into the .env services
	$(API) run python -m investigation_engine.datasets.synthetic

eval-retrieval: ## Compare search configurations on HotpotQA (writes docs/evaluation/)
	$(API) run python -m investigation_engine.evaluation.retrieval \
		--output $(CURDIR)/docs/evaluation/retrieval-hotpotqa.json

eval-chunking: ## Compare chunking strategies on Northwind (needs make services-up)
	$(API) run python -m investigation_engine.evaluation.chunking \
		--output $(CURDIR)/docs/evaluation/chunking-northwind.json

eval-answers: ## Ask the 48 evaluation questions, agent and single-shot (resumable; uses LLM quota)
	$(API) run python -m investigation_engine.evaluation.answers run \
		--output-dir $(CURDIR)/docs/evaluation/answers

eval-cross-check: ## Ask the 28 Northwind questions with the answer cross-check (uses LLM quota)
	$(API) run python -m investigation_engine.evaluation.answers run \
		--output-dir $(CURDIR)/docs/evaluation/answers --config agent-cross-check --northwind-only

eval-report: ## Score the recorded answers (no LLM calls)
	$(API) run python -m investigation_engine.evaluation.answers report \
		--output-dir $(CURDIR)/docs/evaluation/answers

eval-models: ## Compare gpt-5-mini with gpt-oss-120b, same prompt (no LLM calls)
	$(API) run python -m investigation_engine.evaluation.answers compare \
		--output-dir $(CURDIR)/docs/evaluation/answers-prompt-v1 \
		--baseline-dir $(CURDIR)/docs/evaluation/answers-gpt-oss-120b

eval-prompts: ## Compare the current prompt with prompt v1, both on gpt-5-mini (no LLM calls)
	$(API) run python -m investigation_engine.evaluation.answers compare \
		--output-dir $(CURDIR)/docs/evaluation/answers \
		--baseline-dir $(CURDIR)/docs/evaluation/answers-prompt-v1

API_URL ?= https://13-53-155-129.sslip.io

load-test: ## Load-test the read endpoints of API_URL (default: production)
	$(API) run python -m investigation_engine.evaluation.load --base-url $(API_URL) \
		--output $(CURDIR)/docs/evaluation/load-test.json

web-install: ## Install frontend dependencies
	$(WEB) install

web-dev: ## Run the frontend dev server on :5173
	$(WEB) dev

web-format: ## Auto-format frontend code
	$(WEB) format

web-check: ## Run all frontend quality gates (same as CI)
	$(WEB) lint
	$(WEB) format:check
	$(WEB) typecheck
	$(WEB) test
	$(WEB) build
