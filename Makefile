VENV     := .venv/bin
PYTHON   := $(VENV)/python
PIP      := $(PYTHON) -m pip

.PHONY: install install-dev test lint format clean mcp audit preflight sync-claude help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install vibesrails (user mode)
	$(PIP) install -e .

install-dev: ## Install with all dev + MCP dependencies
	$(PIP) install -e ".[dev,mcp,all]"

test: ## Run test suite with timeout
	$(PYTHON) -m pytest tests/ --timeout=60

lint: ## Run ruff linter (auto-fix)
	$(VENV)/ruff check . --fix

format: ## Format code with ruff
	$(VENV)/ruff format .

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ .mypy_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

mcp: ## Start MCP server (stdio)
	$(PYTHON) -m mcp_server

audit: ## Run full vibesrails security scan
	$(VENV)/vibesrails --all

preflight: ## Run pre-session preflight check
	$(VENV)/vibesrails --preflight

sync-claude: ## Auto-generate CLAUDE.md factual sections
	$(VENV)/vibesrails --sync-claude
