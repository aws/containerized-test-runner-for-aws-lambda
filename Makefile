.PHONY: help install dev lint lint-fix format format-fix test check clean lock lock-update docker-build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies from lockfile
	uv sync --frozen --no-dev

dev: ## Install all dependencies (including dev tools)
	uv sync --frozen

lint: ## Run linter
	uv run ruff check src/ test/ run.py

lint-fix: ## Auto-fix lint issues
	uv run ruff check --fix src/ test/ run.py

format: ## Check formatting
	uv run ruff format --check src/ test/ run.py

format-fix: ## Auto-format code
	uv run ruff format src/ test/ run.py

check: lint format ## Run all checks (lint + format)

test: ## Run tests
	uv run python -m pytest test/ -v

lock: ## Update lockfile (respects exclude-newer)
	uv lock

lock-update: ## Update lockfile accepting packages published up to 3 days ago
	uv lock --exclude-newer=$$(date -u -v-3d +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -d '3 days ago' +%Y-%m-%dT00:00:00Z)

docker-build: ## Build docker image locally
	docker build -t containerized-test-runner .

clean: ## Clean generated files
	rm -rf .venv __pycache__ src/*.egg-info .pytest_cache .ruff_cache
