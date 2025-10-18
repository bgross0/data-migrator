# Test Suite

This directory contains all tests for the Data Migrator backend.

## Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and pytest configuration
├── test_example_api.py      # Example API endpoint tests
├── test_example_units.py    # Example unit tests with best practices
├── test_csv_emitter.py      # CSV export functionality tests
├── test_determinism.py      # Determinism verification tests
├── test_normalizers.py      # Data normalizer tests
├── test_registry_loader.py  # Registry loader tests
└── test_validator.py        # Validation logic tests
```

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run with coverage
make all-tests

# Run tests in parallel (faster)
make test-fast
```

### Specific Test Categories

```bash
# Unit tests only (fast, isolated)
make test-unit

# Integration tests only (multiple components)
make test-integration

# Determinism tests
make determinism
```

### Detailed Test Commands

```bash
# Run specific test file
pytest tests/test_example_units.py

# Run specific test class
pytest tests/test_example_api.py::TestDatasetAPI

# Run specific test function
pytest tests/test_example_units.py::TestTransformRegistry::test_trim_transform

# Run tests matching pattern
pytest -k "transform"

# Skip slow tests
pytest -m "not slow"

# Verbose output with print statements
pytest -v -s

# Stop at first failure
pytest -x

# Show local variables in tracebacks
pytest -l
```

## Writing Tests

### Test Categories

We use pytest markers to categorize tests:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with multiple components
- `@pytest.mark.slow` - Tests that take > 1 second
- `@pytest.mark.asyncio` - Async tests

### Test File Naming

- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Using Fixtures

Common fixtures are defined in `conftest.py`:

#### Database Fixtures

```python
def test_with_database(test_db):
    """Use in-memory database for testing."""
    from app.models.source import Dataset

    dataset = Dataset(name="Test", source_type="csv")
    test_db.add(dataset)
    test_db.commit()

    assert dataset.id is not None
```

#### API Client Fixtures

```python
def test_api_endpoint(client):
    """Use FastAPI test client."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
```

#### File System Fixtures

```python
def test_file_operations(temp_dir):
    """Use temporary directory."""
    test_file = temp_dir / "test.csv"
    test_file.write_text("data")
    assert test_file.exists()


def test_with_sample_data(sample_csv_file):
    """Use pre-created sample CSV file."""
    assert sample_csv_file.exists()
    content = sample_csv_file.read_text()
    assert "Name" in content
```

### Example Test Patterns

#### Basic Unit Test

```python
import pytest
from app.core.transformer import TransformRegistry

@pytest.mark.unit
def test_trim_transform():
    """Test string trimming."""
    registry = TransformRegistry()
    trim = registry.get("trim")
    assert trim("  hello  ") == "hello"
```

#### Parametrized Test

```python
@pytest.mark.unit
@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("  spaces  ", "spaces"),
        ("no_spaces", "no_spaces"),
        ("", ""),
    ],
)
def test_trim_various_inputs(input_value, expected):
    """Test trim with multiple inputs."""
    registry = TransformRegistry()
    trim = registry.get("trim")
    assert trim(input_value) == expected
```

#### API Test

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_create_dataset(client: TestClient):
    """Test dataset creation endpoint."""
    response = client.post("/api/v1/datasets", json={
        "name": "Test Dataset",
        "source_type": "csv"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Dataset"
```

#### Exception Test

```python
import pytest

@pytest.mark.unit
def test_division_by_zero():
    """Test that division by zero raises error."""
    with pytest.raises(ZeroDivisionError):
        result = 10 / 0
```

#### Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function(async_client):
    """Test async endpoint."""
    response = await async_client.get("/api/v1/async-endpoint")
    assert response.status_code == 200
```

#### Mock Test

```python
from unittest.mock import Mock, patch

@pytest.mark.unit
@patch("app.core.transformer.external_service")
def test_with_mock(mock_service):
    """Test with mocked external service."""
    mock_service.return_value = {"status": "success"}

    result = mock_service()

    assert result["status"] == "success"
    mock_service.assert_called_once()
```

## Coverage

### Generate Coverage Report

```bash
# Terminal output
make coverage

# HTML report (open htmlcov/index.html)
pytest --cov=app --cov-report=html

# See missing lines
pytest --cov=app --cov-report=term-missing
```

### Coverage Goals

- Aim for > 80% overall coverage
- Critical paths should have 100% coverage
- New features should include tests

## Best Practices

### DO:

- ✅ Write tests for new features
- ✅ Keep tests focused (one thing per test)
- ✅ Use descriptive test names
- ✅ Use fixtures for common setup
- ✅ Mark tests appropriately (unit/integration/slow)
- ✅ Test edge cases and error conditions
- ✅ Use parametrize for multiple similar tests
- ✅ Keep tests fast (< 100ms for unit tests)
- ✅ Mock external dependencies

### DON'T:

- ❌ Write tests that depend on execution order
- ❌ Share state between tests
- ❌ Test implementation details
- ❌ Write overly complex tests
- ❌ Skip writing tests for "simple" code
- ❌ Use sleep() or hardcoded delays
- ❌ Test library code (test YOUR code)
- ❌ Commit failing tests

## CI/CD Integration

Tests run automatically on:
- Pre-commit hooks (local)
- Pull request CI (if configured)
- Pre-merge checks

Ensure all tests pass before pushing code.

## Troubleshooting

### Import Errors

```bash
# Ensure PYTHONPATH is set
PYTHONPATH=. pytest

# Or use Makefile (sets PYTHONPATH)
make test
```

### Database Errors

```bash
# Check that fixtures are being used
def test_something(test_db):  # <- Don't forget this parameter
    ...
```

### Async Errors

```bash
# Ensure async tests are marked
@pytest.mark.asyncio
async def test_something():
    ...
```

### Fixture Not Found

```bash
# Fixtures must be in conftest.py or imported
# Check spelling and availability
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest fixtures](https://docs.pytest.org/en/latest/fixture.html)
- [pytest markers](https://docs.pytest.org/en/latest/example/markers.html)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
