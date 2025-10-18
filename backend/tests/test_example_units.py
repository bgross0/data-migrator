"""
Example unit tests demonstrating best practices for testing core functionality.

Unit tests should be:
- Fast (no database, no external services)
- Isolated (test one thing at a time)
- Independent (can run in any order)
- Repeatable (same result every time)
"""

import pytest
from unittest.mock import Mock, patch

from app.core.transformer import TransformRegistry


@pytest.mark.unit
class TestTransformRegistry:
    """Tests for the Transform Registry."""

    def test_registry_initialization(self):
        """Test that TransformRegistry initializes correctly."""
        registry = TransformRegistry()
        assert registry is not None
        assert hasattr(registry, "get")

    def test_trim_transform(self):
        """Test the trim transform."""
        registry = TransformRegistry()
        trim = registry.get("trim")

        assert trim("  hello  ") == "hello"
        assert trim("world") == "world"
        assert trim("  spaces  everywhere  ") == "spaces  everywhere"

    def test_lower_transform(self):
        """Test the lower transform."""
        registry = TransformRegistry()
        lower = registry.get("lower")

        assert lower("HELLO") == "hello"
        assert lower("World") == "world"
        assert lower("already lowercase") == "already lowercase"

    def test_upper_transform(self):
        """Test the upper transform."""
        registry = TransformRegistry()
        upper = registry.get("upper")

        assert upper("hello") == "HELLO"
        assert upper("World") == "WORLD"
        assert upper("ALREADY UPPERCASE") == "ALREADY UPPERCASE"

    def test_titlecase_transform(self):
        """Test the titlecase transform."""
        registry = TransformRegistry()
        titlecase = registry.get("titlecase")

        assert titlecase("hello world") == "Hello World"
        assert titlecase("LOUD NOISES") == "Loud Noises"
        assert titlecase("mixed Case") == "Mixed Case"

    @pytest.mark.parametrize(
        "input_phone,expected",
        [
            ("+1 (555) 123-4567", "+15551234567"),
            ("555-123-4567", "5551234567"),
            ("(555) 123 4567", "5551234567"),
            ("555.123.4567", "5551234567"),
        ],
    )
    def test_phone_normalize(self, input_phone: str, expected: str):
        """Test phone number normalization with various formats."""
        registry = TransformRegistry()
        normalize = registry.get("phone_normalize")

        result = normalize(input_phone)
        assert result == expected

    @pytest.mark.parametrize(
        "input_email,expected",
        [
            ("  user@example.com  ", "user@example.com"),
            ("USER@EXAMPLE.COM", "user@example.com"),
            ("User@Example.Com", "user@example.com"),
        ],
    )
    def test_email_normalize(self, input_email: str, expected: str):
        """Test email normalization."""
        registry = TransformRegistry()
        normalize = registry.get("email_normalize")

        result = normalize(input_email)
        assert result == expected

    def test_nonexistent_transform_raises_error(self):
        """Test that requesting a non-existent transform raises an error."""
        registry = TransformRegistry()

        with pytest.raises((KeyError, ValueError)):
            registry.get("nonexistent_transform")


@pytest.mark.unit
class TestStringOperations:
    """Example tests for string operations (demonstrating mocking)."""

    def test_split_name_basic(self):
        """Test splitting a full name into first and last."""
        # This would test a hypothetical split_name function
        registry = TransformRegistry()
        split = registry.get("split_name")

        result = split("John Doe")
        # Assuming split_name returns a dict
        assert isinstance(result, (dict, tuple, list))

    @patch("app.core.transformer.some_external_service")
    def test_with_mocked_external_service(self, mock_service):
        """Example of testing code that depends on external services."""
        # Mock the external service
        mock_service.return_value = {"status": "success"}

        # Your code that uses the service would go here
        result = mock_service()

        assert result["status"] == "success"
        mock_service.assert_called_once()


@pytest.mark.unit
class TestDataValidation:
    """Example tests for data validation logic."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", False),
            (None, False),
            ("   ", False),
            ("valid", True),
            ("123", True),
        ],
    )
    def test_is_not_empty(self, value, expected):
        """Test empty value detection."""

        def is_not_empty(val):
            if val is None:
                return False
            if isinstance(val, str) and not val.strip():
                return False
            return True

        assert is_not_empty(value) == expected

    @pytest.mark.parametrize(
        "email,is_valid",
        [
            ("user@example.com", True),
            ("invalid.email", False),
            ("@example.com", False),
            ("user@", False),
            ("", False),
        ],
    )
    def test_email_validation(self, email: str, is_valid: bool):
        """Test email validation."""
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        result = bool(re.match(email_pattern, email))

        assert result == is_valid


@pytest.mark.unit
class TestMathOperations:
    """Example tests for mathematical operations."""

    def test_percentage_calculation(self):
        """Test percentage calculation."""
        total = 100
        part = 25

        percentage = (part / total) * 100

        assert percentage == 25.0

    @pytest.mark.parametrize(
        "values,expected_avg",
        [
            ([1, 2, 3, 4, 5], 3.0),
            ([10, 20, 30], 20.0),
            ([100], 100.0),
        ],
    )
    def test_average_calculation(self, values: list, expected_avg: float):
        """Test average calculation with various inputs."""
        avg = sum(values) / len(values)
        assert avg == expected_avg

    def test_division_by_zero_handling(self):
        """Test that division by zero is handled properly."""
        with pytest.raises(ZeroDivisionError):
            result = 10 / 0


# ===========================
# Fixtures for this module
# ===========================


@pytest.fixture
def sample_registry():
    """Provide a TransformRegistry instance for tests."""
    return TransformRegistry()


@pytest.mark.unit
def test_using_module_fixture(sample_registry):
    """Example test using a module-level fixture."""
    assert sample_registry is not None
    assert isinstance(sample_registry, TransformRegistry)
