# Single entry point for common tasks. Run `make help` to list them.

API := uv --directory apps/api

.DEFAULT_GOAL := help
.PHONY: help api-install api-dev api-format api-check

help: ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

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
