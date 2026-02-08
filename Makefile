.PHONY: install install-dev test lint format clean mcp audit help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install vibesrails (user mode)
	pip install -e .

install-dev: ## Install with all dev + MCP dependencies
	pip install -e ".[dev,mcp,all]"

test: ## Run test suite with timeout
	python -m pytest tests/ --timeout=60

lint: ## Run ruff linter (auto-fix)
	ruff check . --fix

format: ## Format code with ruff
	ruff format .

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .mypy_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

mcp: ## Start MCP server (stdio)
	python -m mcp_server

audit: ## Run full vibesrails security scan
	vibesrails --all
