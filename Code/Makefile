# ============================================================
# SAED-LLM Makefile
# ============================================================
# Tools: uv (Python), pnpm (Node.js)
# ============================================================

.PHONY: help setup install dev dev-api dev-web test lint format clean cleanall

.DEFAULT_GOAL := help

# ------------------------------------------------------------
# Variables
# ------------------------------------------------------------

UV := . .venv/bin/activate && uv
PYTHON := $(UV) run python
PNPM := pnpm

# ------------------------------------------------------------
# Help
# ------------------------------------------------------------

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ------------------------------------------------------------
# Setup & Install
# ------------------------------------------------------------

setup: ## First-time setup: check tools, create venv, copy config, install deps
	@echo "Checking required tools..."
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@command -v pnpm >/dev/null 2>&1 || { echo "Error: pnpm is not installed. Install: npm install -g pnpm"; exit 1; }
	@if [ ! -f data/config.json ]; then \
		cp data/config.example.json data/config.json; \
		echo "Created data/config.json from config.example.json"; \
	fi
	@$(MAKE) venv
	@$(MAKE) install
	@$(MAKE) init-data
	@echo "Setup complete!"

venv: ## Ensure Python 3.12 venv is created via uv
	@echo "Ensuring Python 3.12 interpreter..."
	@cd backend && uv python install 3.12
	@echo "Ensuring backend/.venv exists..."
	@cd backend && uv venv --python 3.12
	@echo "Virtual environment ready (backend/.venv)."

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	@cd backend && . .venv/bin/activate && uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple
	@echo "Installing frontend dependencies..."
	@cd frontend && $(PNPM) install
	@echo "Done."

init-data: ## Initialize data registries (ontologies, tables, labels, batches)
	@echo "Initializing ontologies registry..."
	@cd backend && $(UV) run python scripts/migrate_ontologies_registry.py --non-interactive
	@echo "Initializing tables registry..."
	@cd backend && $(UV) run python scripts/migrate_tables_registry.py --non-interactive
	@echo "Initializing labels registry..."
	@cd backend && $(UV) run python scripts/migrate_labels_registry.py --non-interactive
	@echo "Initializing batches registry..."
	@cd backend && $(UV) run python scripts/migrate_batches_registry.py --non-interactive
	@echo "Data registries initialized."

# ------------------------------------------------------------
# Development
# ------------------------------------------------------------

dev: ## Run both backend and frontend
	@echo "Starting development servers..."
	@$(MAKE) -j2 dev-api dev-web

dev-api: ## Run backend API server (port 8000)
	@cd backend && $(UV) run uvicorn saed.api.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Run frontend dev server (port 3000)
	@cd frontend && $(PNPM) dev

# ------------------------------------------------------------
# Test & Lint
# ------------------------------------------------------------

test: ## Run tests
	@cd backend && $(UV) run pytest

lint: ## Run linters
	@echo "Linting backend..."
	@cd backend && $(UV) run ruff check src/
	@echo "Linting frontend..."
	@cd frontend && $(PNPM) lint

format: ## Format code
	@echo "Formatting backend..."
	@cd backend && $(UV) run ruff format src/
	@cd backend && $(UV) run ruff check --fix src/
	@echo "Formatting frontend..."
	@cd frontend && $(PNPM) format 2>/dev/null || true

# ------------------------------------------------------------
# Clean
# ------------------------------------------------------------

clean: ## Remove cache files
	@echo "Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/.next 2>/dev/null || true
	@rm -rf frontend/.turbo 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@echo "Done."

cleanall: clean ## Remove all dependencies and build artifacts
	@echo "Removing dependencies and build artifacts..."
	@rm -rf backend/.venv 2>/dev/null || true
	@rm -rf backend/dist 2>/dev/null || true
	@find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/node_modules 2>/dev/null || true
	@rm -rf frontend/out 2>/dev/null || true
	@echo "Done. Run 'make install' to reinstall dependencies."
