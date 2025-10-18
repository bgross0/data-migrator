# Development Guide

This guide covers development tools, workflows, and best practices for contributing to Data Migrator.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Tools](#development-tools)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Development Workflow](#development-workflow)
- [Makefile Commands](#makefile-commands)

---

## Quick Start

### 1. Initial Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
make install-dev

# Set up pre-commit hooks
make setup-pre-commit

# Apply database migrations
make db-upgrade
```

### 2. Run Development Server

```bash
make run
# Server will be available at http://localhost:8888
```

### 3. Run Tests

```bash
make test           # Run core test suite
make all-tests      # Run all tests with coverage
make test-fast      # Run tests in parallel
```

---

## Development Tools

We use a comprehensive set of tools to maintain code quality:

### Code Formatting

- **[Black](https://black.readthedocs.io/)** - The uncompromising Python code formatter
  - Automatically formats code to a consistent style
  - Line length: 100 characters
  - Target: Python 3.11+

- **[Ruff](https://docs.astral.sh/ruff/)** - An extremely fast Python linter and formatter
  - Replaces: flake8, isort, pyupgrade, and more
  - Automatically fixes many issues
  - Enforces import sorting

### Type Checking

- **[mypy](https://mypy-lang.org/)** - Static type checker for Python
  - Catches type-related bugs before runtime
  - Ensures type hints are correct
  - Configured to be lenient initially (can be tightened over time)

### Testing

- **[pytest](https://pytest.org/)** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-xdist** - Parallel test execution
- **pytest-mock** - Mocking support
- **factory-boy** - Test data factories
- **faker** - Generate fake data for tests

### Security

- **[Bandit](https://bandit.readthedocs.io/)** - Security issue scanner
  - Finds common security issues in Python code
  - Runs automatically in pre-commit hooks

### Pre-commit Hooks

- **[pre-commit](https://pre-commit.com/)** - Git hook framework
  - Runs checks automatically before commits
  - Ensures code quality standards are met
  - Can auto-fix many issues

---

## Code Quality

### Running Code Quality Checks

```bash
# Format code (Black + Ruff)
make format

# Lint code (Ruff)
make lint

# Type check (mypy)
make type-check

# Run all checks (format + lint + type-check + test)
make check

# Run pre-commit hooks manually
make pre-commit
```

### Code Style Guidelines

1. **Follow PEP 8** - Python style guide (enforced by Ruff)
2. **Use type hints** - Add type annotations to function signatures
3. **Write docstrings** - Document modules, classes, and functions
4. **Keep functions small** - Each function should do one thing
5. **Avoid complexity** - Keep cyclomatic complexity low
6. **No hardcoded values** - Use constants or configuration

### Example: Well-Formatted Code

```python
from typing import List, Optional

def process_records(
    records: List[dict],
    max_count: Optional[int] = None,
) -> List[dict]:
    """
    Process a list of records with optional limit.

    Args:
        records: List of record dictionaries to process
        max_count: Maximum number of records to process (None = all)

    Returns:
        List of processed records

    Raises:
        ValueError: If records list is empty
    """
    if not records:
        raise ValueError("Records list cannot be empty")

    processed = [_process_single_record(r) for r in records]

    if max_count is not None:
        return processed[:max_count]

    return processed


def _process_single_record(record: dict) -> dict:
    """Process a single record (helper function)."""
    return {**record, "processed": True}
```

---

## Testing

### Test Structure

```
backend/tests/
├── __init__.py              # Test package init
├── conftest.py              # Shared fixtures and configuration
├── test_example_api.py      # Example API tests
├── test_example_units.py    # Example unit tests
├── test_csv_emitter.py      # CSV emitter tests
├── test_determinism.py      # Determinism verification
├── test_normalizers.py      # Data normalizer tests
├── test_registry_loader.py  # Registry loader tests
└── test_validator.py        # Validation tests
```

### Writing Tests

#### Unit Tests (Fast, Isolated)

```python
import pytest
from app.core.transformer import TransformRegistry

@pytest.mark.unit
def test_trim_transform():
    """Test the trim transform."""
    registry = TransformRegistry()
    trim = registry.get("trim")
    assert trim("  hello  ") == "hello"
```

#### Integration Tests (Multiple Components)

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_dataset_lifecycle(client: TestClient):
    """Test complete dataset CRUD lifecycle."""
    # Create
    response = client.post("/api/v1/datasets", json={
        "name": "Test Dataset",
        "source_type": "csv"
    })
    assert response.status_code == 201
    dataset_id = response.json()["id"]

    # Read
    response = client.get(f"/api/v1/datasets/{dataset_id}")
    assert response.status_code == 200

    # Delete
    response = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert response.status_code == 204
```

#### Using Fixtures

```python
def test_with_database(test_db):
    """Test using database fixture."""
    from app.models.source import Dataset

    dataset = Dataset(name="Test", source_type="csv")
    test_db.add(dataset)
    test_db.commit()

    assert dataset.id is not None


def test_api_endpoint(client):
    """Test using test client fixture."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
```

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make coverage
# Open htmlcov/index.html in browser to see coverage report

# Run tests in parallel (faster)
make test-fast

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only

# Run specific test file
pytest tests/test_example_units.py

# Run specific test
pytest tests/test_example_units.py::TestTransformRegistry::test_trim_transform

# Run tests matching pattern
pytest -k "transform"

# Run with verbose output
pytest -v -s

# Skip slow tests
pytest -m "not slow"
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit           # Fast, isolated tests
@pytest.mark.integration    # Multi-component tests
@pytest.mark.slow           # Tests that take > 1 second
@pytest.mark.asyncio        # Async tests
```

---

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality.

### Setup

```bash
# Install hooks (one-time setup)
make setup-pre-commit
```

### What Gets Checked

When you commit, these checks run automatically:

1. **Ruff** - Linting and auto-fixes
2. **Black** - Code formatting
3. **mypy** - Type checking (on app/ only)
4. **Bandit** - Security scanning
5. **General checks**:
   - Trailing whitespace
   - End of file newlines
   - YAML/JSON/TOML syntax
   - Large files (> 1MB)
   - Merge conflicts
   - Private keys
   - Python syntax
   - Debug statements

### Manual Execution

```bash
# Run all hooks on all files
make pre-commit

# Or use pre-commit directly
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

### Updating Hooks

```bash
# Update hook versions
pre-commit autoupdate
```

---

## Development Workflow

### Standard Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**
   - Write code
   - Add tests
   - Run checks locally

3. **Run quality checks**
   ```bash
   make check  # Runs format, lint, type-check, test
   ```

4. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   # Pre-commit hooks run automatically
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

### Database Migrations

When you change models:

```bash
# Create migration
make db-migrate
# Enter migration name when prompted

# Review generated migration in alembic/versions/

# Apply migration
make db-upgrade

# Rollback if needed
make db-downgrade
```

### Debugging

```bash
# Use ipdb for debugging
pip install ipdb

# In your code:
import ipdb; ipdb.set_trace()

# Or use ipython for interactive exploration
ipython
```

---

## Makefile Commands

Run `make help` or just `make` to see all available commands:

### Setup Commands

| Command | Description |
|---------|-------------|
| `make install` | Install production dependencies |
| `make install-dev` | Install development dependencies |
| `make setup-pre-commit` | Set up pre-commit hooks |

### Testing Commands

| Command | Description |
|---------|-------------|
| `make test` | Run core test suite |
| `make all-tests` | Run all tests with coverage |
| `make test-fast` | Run tests in parallel |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make coverage` | Generate HTML coverage report |
| `make determinism` | Test export determinism |

### Code Quality Commands

| Command | Description |
|---------|-------------|
| `make format` | Format code with Black and Ruff |
| `make lint` | Lint code with Ruff |
| `make type-check` | Run mypy type checking |
| `make check` | Run all checks |
| `make pre-commit` | Run pre-commit hooks |

### Development Commands

| Command | Description |
|---------|-------------|
| `make run` | Start development server |
| `make db-upgrade` | Apply database migrations |
| `make db-migrate` | Create new migration |
| `make db-downgrade` | Rollback one migration |
| `make demo` | Run demo pipeline |

### Cleanup Commands

| Command | Description |
|---------|-------------|
| `make clean` | Remove generated files/caches |
| `make clean-all` | Clean everything including venv |

---

## Configuration Files

### `pyproject.toml`

Central configuration for all Python tools:
- Black formatting rules
- Ruff linting rules
- mypy type checking rules
- pytest configuration
- Coverage settings
- Bandit security rules

### `.pre-commit-config.yaml`

Defines pre-commit hooks and their versions.

### `requirements.txt`

Production dependencies.

### `requirements-dev.txt`

Development dependencies (includes production deps).

---

## Best Practices

### DO:
- ✅ Write tests for new features
- ✅ Add type hints to function signatures
- ✅ Run `make check` before committing
- ✅ Keep commits small and focused
- ✅ Write clear commit messages
- ✅ Document complex logic
- ✅ Use fixtures for test data
- ✅ Mark tests appropriately (unit/integration)

### DON'T:
- ❌ Skip pre-commit hooks
- ❌ Commit code that fails tests
- ❌ Leave debug statements in code
- ❌ Use `as any` type casts (TypeScript) or `type: ignore` (Python) without justification
- ❌ Hardcode credentials or secrets
- ❌ Commit large files (> 1MB)
- ❌ Leave commented-out code

---

## Troubleshooting

### Pre-commit hooks failing

```bash
# Install hooks
make setup-pre-commit

# Run manually to see errors
make pre-commit
```

### Tests failing

```bash
# Run with verbose output
pytest -v -s

# Run specific test to isolate issue
pytest tests/test_example.py::test_function -v -s
```

### Type checking errors

```bash
# Run mypy with verbose output
venv/bin/mypy app/ --show-error-codes

# Ignore specific errors (last resort)
# type: ignore[error-code]
```

### Import errors in tests

```bash
# Make sure PYTHONPATH is set
PYTHONPATH=. pytest

# Or use the Makefile (sets PYTHONPATH automatically)
make test
```

---

## Additional Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy-lang.org/)
- [pytest Documentation](https://pytest.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#session-testing)

---

## Getting Help

If you run into issues:

1. Check this guide
2. Check the main [CLAUDE.md](./CLAUDE.md) for project-specific patterns
3. Run `make help` to see available commands
4. Ask team members or create an issue
