.PHONY: help install install-dev demo test determinism clean all-tests test-fast
.PHONY: format lint type-check check pre-commit coverage
.DEFAULT_GOAL := help

# ===========================
# Help
# ===========================

help:  ## Show this help message
	@echo "Data Migrator - Backend Makefile"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ===========================
# Setup
# ===========================

install:  ## Install production dependencies
	@echo "📦 Installing production dependencies..."
	@pip install -r requirements.txt
	@echo "✅ Production dependencies installed!"

install-dev:  ## Install development dependencies
	@echo "📦 Installing development dependencies..."
	@pip install -r requirements-dev.txt
	@echo "✅ Development dependencies installed!"

setup-pre-commit:  ## Set up pre-commit hooks
	@echo "🔧 Setting up pre-commit hooks..."
	@pre-commit install
	@echo "✅ Pre-commit hooks installed!"

# ===========================
# Testing
# ===========================

test:  ## Run core test suite
	@echo "🧪 Running test suite..."
	@PYTHONPATH=. venv/bin/pytest -v tests/test_registry_loader.py tests/test_normalizers.py tests/test_validator.py tests/test_csv_emitter.py
	@echo ""
	@echo "✅ All tests passed!"

test-fast:  ## Run tests in parallel (fast)
	@echo "🧪 Running tests in parallel..."
	@PYTHONPATH=. venv/bin/pytest -v -n auto
	@echo "✅ Tests complete!"

all-tests:  ## Run full test suite with coverage
	@echo "🧪 Running full test suite..."
	@PYTHONPATH=. venv/bin/pytest -v
	@echo ""
	@echo "📊 Test coverage:"
	@PYTHONPATH=. venv/bin/pytest --cov=app --cov-report=term-missing
	@echo ""
	@echo "✅ Full test suite complete!"

coverage:  ## Generate HTML coverage report
	@echo "📊 Generating coverage report..."
	@PYTHONPATH=. venv/bin/pytest --cov=app --cov-report=html --cov-report=term
	@echo ""
	@echo "✅ Coverage report generated in htmlcov/index.html"

determinism:  ## Test determinism (byte-identical exports)
	@echo "🔍 Testing determinism (byte-identical exports)..."
	@PYTHONPATH=. venv/bin/pytest -v tests/test_determinism.py
	@echo ""
	@echo "✅ Determinism verified: SHA256 hashes match!"

test-unit:  ## Run only unit tests
	@echo "🧪 Running unit tests..."
	@PYTHONPATH=. venv/bin/pytest -v -m unit
	@echo "✅ Unit tests complete!"

test-integration:  ## Run only integration tests
	@echo "🧪 Running integration tests..."
	@PYTHONPATH=. venv/bin/pytest -v -m integration
	@echo "✅ Integration tests complete!"

# ===========================
# Code Quality
# ===========================

format:  ## Format code with Black and Ruff
	@echo "🎨 Formatting code..."
	@venv/bin/black app/ tests/
	@venv/bin/ruff check --fix app/ tests/
	@echo "✅ Code formatted!"

lint:  ## Lint code with Ruff
	@echo "🔍 Linting code..."
	@venv/bin/ruff check app/ tests/
	@echo "✅ Linting complete!"

type-check:  ## Run type checking with mypy
	@echo "🔍 Running type checks..."
	@venv/bin/mypy app/
	@echo "✅ Type checking complete!"

check:  ## Run all checks (format, lint, type-check, test)
	@echo "🔍 Running all checks..."
	@$(MAKE) format
	@$(MAKE) lint
	@$(MAKE) type-check
	@$(MAKE) test
	@echo ""
	@echo "✅ All checks passed!"

pre-commit:  ## Run pre-commit hooks on all files
	@echo "🔍 Running pre-commit hooks..."
	@pre-commit run --all-files
	@echo "✅ Pre-commit checks complete!"

# ===========================
# Development
# ===========================

demo:  ## Run demo export pipeline
	@echo "🚀 Running demo export pipeline..."
	@echo "📦 Creating output directory..."
	@mkdir -p out/demo
	@echo "✓ Output directory created"
	@echo ""
	@echo "Note: Full demo requires database setup."
	@echo "Run 'make test' to verify all components work."
	@echo ""

run:  ## Run development server
	@echo "🚀 Starting development server..."
	@uvicorn app.main:app --reload --port 8888

db-upgrade:  ## Apply database migrations
	@echo "📊 Applying database migrations..."
	@./venv/bin/alembic upgrade head
	@echo "✅ Migrations applied!"

db-migrate:  ## Create new database migration
	@read -p "Migration name: " name; \
	echo "📝 Creating migration: $$name"; \
	./venv/bin/alembic revision --autogenerate -m "$$name"

db-downgrade:  ## Rollback one database migration
	@echo "⏪ Rolling back one migration..."
	@./venv/bin/alembic downgrade -1
	@echo "✅ Rollback complete!"

# ===========================
# Cleanup
# ===========================

clean:  ## Clean generated files and caches
	@echo "🧹 Cleaning output directories..."
	@rm -rf out/demo
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✓ Cleanup complete"

clean-all: clean  ## Clean everything including venv
	@echo "🧹 Removing virtual environment..."
	@rm -rf venv/
	@echo "✓ Deep cleanup complete"
