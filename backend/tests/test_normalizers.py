"""
Tests for normalizers module.

Validates:
- Idempotency (normalized(normalized(x)) == normalized(x))
- Edge cases
- Error handling
- Synonym resolution
"""
import pytest
from app.transform.normalizers import (
    normalize_phone_us,
    normalize_email,
    normalize_date_any,
    coerce_bool,
    coerce_enum,
    NormalizeError,
)


class TestNormalizePhoneUS:
    """Tests for normalize_phone_us."""

    def test_ten_digit_phone(self):
        """Test 10-digit phone gets country code added."""
        assert normalize_phone_us("5551234567") == "15551234567"
        assert normalize_phone_us("(555) 123-4567") == "15551234567"
        assert normalize_phone_us("555-123-4567") == "15551234567"

    def test_eleven_digit_phone_with_1(self):
        """Test 11-digit phone with leading 1 is preserved."""
        assert normalize_phone_us("15551234567") == "15551234567"
        assert normalize_phone_us("1 (555) 123-4567") == "15551234567"
        assert normalize_phone_us("1-555-123-4567") == "15551234567"

    def test_idempotency(self):
        """Test that normalizing twice gives same result."""
        normalized = normalize_phone_us("(555) 123-4567")
        assert normalize_phone_us(normalized) == normalized

    def test_formatting_stripped(self):
        """Test various formatting is removed."""
        assert normalize_phone_us("+1 (555) 123-4567") == "15551234567"
        assert normalize_phone_us("555.123.4567") == "15551234567"
        assert normalize_phone_us("555 123 4567") == "15551234567"

    def test_invalid_length_raises(self):
        """Test invalid lengths raise NormalizeError."""
        with pytest.raises(NormalizeError, match="expected 10 or 11 digits"):
            normalize_phone_us("123")

        with pytest.raises(NormalizeError, match="expected 10 or 11 digits"):
            normalize_phone_us("12345678901234567")

    def test_empty_raises(self):
        """Test empty input raises error."""
        with pytest.raises(NormalizeError, match="empty or None"):
            normalize_phone_us(None)

        with pytest.raises(NormalizeError, match="empty or None"):
            normalize_phone_us("")


class TestNormalizeEmail:
    """Tests for normalize_email."""

    def test_lowercase_conversion(self):
        """Test email is converted to lowercase."""
        assert normalize_email("USER@EXAMPLE.COM") == "user@example.com"
        assert normalize_email("User@Example.Com") == "user@example.com"

    def test_whitespace_stripped(self):
        """Test whitespace is removed."""
        assert normalize_email("  user@example.com  ") == "user@example.com"
        assert normalize_email("\tuser@example.com\n") == "user@example.com"

    def test_idempotency(self):
        """Test that normalizing twice gives same result."""
        normalized = normalize_email("USER@EXAMPLE.COM")
        assert normalize_email(normalized) == normalized

    def test_valid_formats(self):
        """Test various valid email formats."""
        assert normalize_email("user+tag@example.com") == "user+tag@example.com"
        assert normalize_email("user.name@example.co.uk") == "user.name@example.co.uk"
        assert normalize_email("user_123@example.com") == "user_123@example.com"

    def test_invalid_format_raises(self):
        """Test invalid formats raise NormalizeError."""
        with pytest.raises(NormalizeError, match="Invalid email"):
            normalize_email("not-an-email")

        with pytest.raises(NormalizeError, match="Invalid email"):
            normalize_email("@example.com")

        with pytest.raises(NormalizeError, match="Invalid email"):
            normalize_email("user@")

    def test_empty_raises(self):
        """Test empty input raises error."""
        with pytest.raises(NormalizeError, match="empty or None"):
            normalize_email(None)

        with pytest.raises(NormalizeError, match="empty or None"):
            normalize_email("")


class TestNormalizeDateAny:
    """Tests for normalize_date_any."""

    def test_iso_format(self):
        """Test ISO format dates."""
        assert normalize_date_any("2024-01-15") == "2024-01-15"
        assert normalize_date_any("2024-12-31") == "2024-12-31"

    def test_idempotency(self):
        """Test that normalizing twice gives same result."""
        normalized = normalize_date_any("01/15/2024")
        assert normalize_date_any(normalized) == normalized

    def test_us_format(self):
        """Test US format (mm/dd/yyyy)."""
        assert normalize_date_any("01/15/2024") == "2024-01-15"
        assert normalize_date_any("12/31/2024") == "2024-12-31"
        assert normalize_date_any("01-15-2024") == "2024-01-15"

    def test_eu_format(self):
        """Test EU format (dd/mm/yyyy)."""
        # Note: Ambiguous dates may parse as US format first
        assert normalize_date_any("31/12/2024") == "2024-12-31"  # Unambiguous
        assert normalize_date_any("15/01/2024") == "2024-01-15"  # Unambiguous

    def test_named_months(self):
        """Test formats with month names."""
        assert normalize_date_any("Jan 15, 2024") == "2024-01-15"
        assert normalize_date_any("January 15, 2024") == "2024-01-15"
        assert normalize_date_any("15 Jan 2024") == "2024-01-15"
        assert normalize_date_any("15 January 2024") == "2024-01-15"

    def test_compact_format(self):
        """Test compact format (YYYYMMDD)."""
        assert normalize_date_any("20240115") == "2024-01-15"

    def test_excel_serial(self):
        """Test Excel serial date numbers."""
        # Excel serial 44927 = 2023-01-01
        assert normalize_date_any("44927") == "2023-01-01"

    def test_invalid_date_raises(self):
        """Test invalid dates raise NormalizeError."""
        with pytest.raises(NormalizeError, match="Cannot parse date"):
            normalize_date_any("not-a-date")

        with pytest.raises(NormalizeError, match="Cannot parse date"):
            normalize_date_any("13/32/2024")  # Invalid day/month

    def test_empty_raises(self):
        """Test empty input raises error."""
        with pytest.raises(NormalizeError, match="empty or None"):
            normalize_date_any(None)

        with pytest.raises(NormalizeError, match="empty or None"):
            normalize_date_any("")


class TestCoerceBool:
    """Tests for coerce_bool."""

    def test_truthy_values(self):
        """Test various truthy values."""
        assert coerce_bool("yes") == "true"
        assert coerce_bool("y") == "true"
        assert coerce_bool("true") == "true"
        assert coerce_bool("t") == "true"
        assert coerce_bool("1") == "true"
        assert coerce_bool(True) == "true"

    def test_falsy_values(self):
        """Test various falsy values."""
        assert coerce_bool("no") == "false"
        assert coerce_bool("n") == "false"
        assert coerce_bool("false") == "false"
        assert coerce_bool("f") == "false"
        assert coerce_bool("0") == "false"
        assert coerce_bool(False) == "false"

    def test_idempotency(self):
        """Test that coercing twice gives same result."""
        assert coerce_bool("true") == "true"
        assert coerce_bool("false") == "false"
        assert coerce_bool(coerce_bool("yes")) == "true"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert coerce_bool("YES") == "true"
        assert coerce_bool("True") == "true"
        assert coerce_bool("FALSE") == "false"

    def test_invalid_value_raises(self):
        """Test invalid values raise NormalizeError."""
        with pytest.raises(NormalizeError, match="Cannot coerce to boolean"):
            coerce_bool("maybe")

        with pytest.raises(NormalizeError, match="Cannot coerce to boolean"):
            coerce_bool("123")

    def test_empty_raises(self):
        """Test empty input raises error."""
        with pytest.raises(NormalizeError, match="empty or None"):
            coerce_bool(None)

        with pytest.raises(NormalizeError, match="empty or None"):
            coerce_bool("")


class TestCoerceEnum:
    """Tests for coerce_enum with synonym resolution."""

    def test_synonym_resolution(self):
        """Test that synonyms are resolved to canonical values."""
        synonyms = {"won": "stage_won", "closed": "stage_won"}
        mapping = {}

        assert coerce_enum("won", mapping, synonyms) == "stage_won"
        assert coerce_enum("closed", mapping, synonyms) == "stage_won"

    def test_inline_mapping(self):
        """Test inline mapping resolution."""
        mapping = {"lead": "lead", "opp": "opportunity"}
        synonyms = {}

        assert coerce_enum("lead", mapping, synonyms) == "lead"
        assert coerce_enum("opp", mapping, synonyms) == "opportunity"

    def test_already_canonical(self):
        """Test that canonical values pass through (idempotency)."""
        synonyms = {"won": "stage_won"}
        mapping = {}

        assert coerce_enum("stage_won", mapping, synonyms) == "stage_won"

    def test_synonym_precedence(self):
        """Test that synonyms are checked before inline mapping."""
        synonyms = {"lead": "stage_lead"}
        mapping = {"lead": "different_value"}

        # Synonym should win
        assert coerce_enum("lead", mapping, synonyms) == "stage_lead"

    def test_invalid_value_raises(self):
        """Test unknown values raise NormalizeError."""
        synonyms = {"won": "stage_won"}
        mapping = {}

        with pytest.raises(NormalizeError, match="Unknown enum value"):
            coerce_enum("unknown_stage", mapping, synonyms)

    def test_empty_raises(self):
        """Test empty input raises error."""
        with pytest.raises(NormalizeError, match="empty or None"):
            coerce_enum(None, {}, {})

        with pytest.raises(NormalizeError, match="empty or None"):
            coerce_enum("", {}, {})

    def test_none_mappings(self):
        """Test behavior with None mappings."""
        with pytest.raises(NormalizeError, match="Unknown enum value"):
            coerce_enum("value", None, None)


class TestIdempotency:
    """Test idempotency across all normalizers."""

    def test_phone_idempotent(self):
        """Test phone normalization is idempotent."""
        phone = "(555) 123-4567"
        n1 = normalize_phone_us(phone)
        n2 = normalize_phone_us(n1)
        n3 = normalize_phone_us(n2)
        assert n1 == n2 == n3

    def test_email_idempotent(self):
        """Test email normalization is idempotent."""
        email = "USER@EXAMPLE.COM"
        n1 = normalize_email(email)
        n2 = normalize_email(n1)
        n3 = normalize_email(n2)
        assert n1 == n2 == n3

    def test_date_idempotent(self):
        """Test date normalization is idempotent."""
        date = "01/15/2024"
        n1 = normalize_date_any(date)
        n2 = normalize_date_any(n1)
        n3 = normalize_date_any(n2)
        assert n1 == n2 == n3

    def test_bool_idempotent(self):
        """Test bool coercion is idempotent."""
        value = "yes"
        n1 = coerce_bool(value)
        n2 = coerce_bool(n1)
        n3 = coerce_bool(n2)
        assert n1 == n2 == n3

    def test_enum_idempotent(self):
        """Test enum coercion is idempotent."""
        synonyms = {"won": "stage_won"}
        mapping = {}

        value = "won"
        n1 = coerce_enum(value, mapping, synonyms)
        n2 = coerce_enum(n1, mapping, synonyms)
        n3 = coerce_enum(n2, mapping, synonyms)
        assert n1 == n2 == n3
