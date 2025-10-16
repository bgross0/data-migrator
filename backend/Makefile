.PHONY: demo test determinism clean

demo:
	@echo "🚀 Running demo export pipeline..."
	@echo "📦 Creating output directory..."
	@mkdir -p out/demo
	@echo "✓ Output directory created"
	@echo ""
	@echo "Note: Full demo requires database setup."
	@echo "Run 'make test' to verify all components work."
	@echo ""

test:
	@echo "🧪 Running test suite..."
	pytest -v tests/test_registry_loader.py tests/test_normalizers.py tests/test_validator.py tests/test_csv_emitter.py
	@echo ""
	@echo "✅ All tests passed!"

determinism:
	@echo "🔍 Testing determinism (byte-identical exports)..."
	@PYTHONPATH=. venv/bin/pytest -v tests/test_determinism.py
	@echo ""
	@echo "✅ Determinism verified: SHA256 hashes match!"

clean:
	@echo "🧹 Cleaning output directories..."
	@rm -rf out/demo
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete"

all-tests:
	@echo "🧪 Running full test suite..."
	@pytest -v
	@echo ""
	@echo "📊 Test coverage:"
	@pytest --cov=app --cov-report=term-missing
	@echo ""
	@echo "✅ Full test suite complete!"
