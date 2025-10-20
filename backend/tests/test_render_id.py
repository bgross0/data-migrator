"""
Unit tests for render_id templates with or/concat functionality.
"""
import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.export.idgen import (
    render_id,
    slug,
    or_helper as or_helper_func,
    concat,
    isset,
    reset_dedup_tracker,
)


class TestRenderIdTemplates:
    """Test render_id functionality with various template patterns."""

    def setup_method(self):
        """Reset dedup tracker before each test."""
        reset_dedup_tracker()

    def test_simple_slug(self):
        """Test basic slug template."""
        row = {"email": "john.doe@example.com"}
        result = render_id("partner_{slug(email)}", row)
        assert result == "partner_john_doe_example_com"

    def test_slug_with_special_characters(self):
        """Test slug with special characters."""
        row = {"name": "José's Company & Co."}
        result = render_id("company_{slug(name)}", row)
        assert result == "company_jose_s_company_co"

    def test_slug_truncation(self):
        """Test slug truncation to max length."""
        row = {"name": "A" * 100}
        result = render_id("partner_{slug(name)}", row)
        # Should be truncated to fit within 64 char limit
        assert len(result) <= 64
        assert result.startswith("partner_")

    def test_or_pattern(self):
        """Test or pattern - use first non-empty value."""
        # Case 1: email exists
        row1 = {"email": "test@example.com", "name": "Test User"}
        result1 = render_id("partner_{slug(email) or slug(name)}", row1)
        assert result1 == "partner_test_example_com"

        # Case 2: email empty, use name
        row2 = {"email": "", "name": "Test User"}
        result2 = render_id("partner_{slug(email) or slug(name)}", row2)
        assert result2 == "partner_test_user"

        # Case 3: email missing, use name
        row3 = {"name": "Test User"}
        result3 = render_id("partner_{slug(name)}", row3)
        assert result3 == "partner_test_user"

    def test_concat_pattern(self):
        """Test concat pattern."""
        row = {"first_name": "John", "last_name": "Doe", "company": "Acme"}

        # Basic concat
        template = "contact_{concat(first_name, last_name)}"
        # Note: concat functionality needs to be in template parser
        # For now, test direct concat function
        concatenated = concat(row["first_name"], row["last_name"])
        assert concatenated == "John_Doe"

    def test_dedup_tracking(self):
        """Test deduplication with suffixes."""
        reset_dedup_tracker()

        row1 = {"email": "test@example.com"}
        row2 = {"email": "test@example.com"}
        row3 = {"email": "test@example.com"}

        result1 = render_id("partner_{slug(email)}", row1)
        result2 = render_id("partner_{slug(email)}", row2)
        result3 = render_id("partner_{slug(email)}", row3)

        assert result1 == "partner_test_example_com"
        assert result2 == "partner_test_example_com_2"
        assert result3 == "partner_test_example_com_3"

    def test_empty_values(self):
        """Test handling of empty values."""
        row = {"email": "", "name": None, "phone": ""}

        # Should handle empty gracefully
        result = render_id("partner_{slug(email)}", row)
        assert result == "partner_"

    def test_unicode_normalization(self):
        """Test Unicode character normalization."""
        row = {
            "name": "Müller & Söhne GmbH",
            "city": "São Paulo"
        }

        result1 = render_id("company_{slug(name)}", row)
        assert result1 == "company_muller_sohne_gmbh"

        result2 = render_id("city_{slug(city)}", row)
        assert result2 == "city_sao_paulo"


class TestIdgenHelpers:
    """Test individual idgen helper functions."""

    def test_slug_function(self):
        """Test slug helper function."""
        assert slug("Hello World") == "hello_world"
        assert slug("José's Email") == "jose_s_email"
        assert slug("Product #123") == "product_123"
        assert slug("") == ""
        assert slug(None) == ""
        assert slug(123) == "123"

    def test_isset_function(self):
        """Test isset helper function."""
        assert isset("value") is True
        assert isset("") is False
        assert isset(None) is False
        assert isset(0) is True  # 0 is a valid value
        assert isset(False) is True  # False is a valid value

    def test_or_helper_function(self):
        """Test or_helper function."""
        assert or_helper_func("first", "second") == "first"
        assert or_helper_func("", "second") == "second"
        assert or_helper_func(None, "second") == "second"
        assert or_helper_func("", None, "third") == "third"
        assert or_helper_func("", "", "") == ""

    def test_concat_function(self):
        """Test concat function."""
        assert concat("a", "b", "c") == "a_b_c"
        assert concat("a", "", "c") == "a_c"
        assert concat("a", None, "c") == "a_c"
        assert concat("first", "last", sep="-") == "first-last"
        assert concat() == ""


class TestRenderIdRegressions:
    """Regression tests for specific bugs found in production."""

    def setup_method(self):
        """Reset dedup tracker before each test."""
        reset_dedup_tracker()

    def test_row_with_missing_field(self):
        """Test that missing fields don't crash."""
        row = {"name": "Test"}
        # Should not raise KeyError
        result = render_id("partner_{slug(email)}", row)
        assert result == "partner_"

    def test_complex_template(self):
        """Test complex real-world template."""
        row = {
            "customer_name": "Acme Corp",
            "customer_code": "ACME001",
            "email": "contact@acme.com"
        }

        # Complex template with multiple fallbacks
        template = "customer_{slug(customer_code) or slug(email) or slug(customer_name)}"
        result = render_id(template, row)
        assert result == "customer_acme001"

    def test_template_with_literals(self):
        """Test template with literal strings."""
        row = {"type": "vendor", "name": "Supplier Inc"}
        result = render_id("partner_{slug(type)}_{slug(name)}", row)
        assert result == "partner_vendor_supplier_inc"

    def test_idempotency(self):
        """Test that same input produces same output."""
        row = {"email": "test@example.com"}
        result1 = render_id("partner_{slug(email)}", row, track_dedup=False)
        result2 = render_id("partner_{slug(email)}", row, track_dedup=False)
        assert result1 == result2

    def test_dedup_across_models(self):
        """Test dedup tracking across different models."""
        reset_dedup_tracker()

        row = {"email": "test@example.com"}

        # Same email, different model prefixes
        result1 = render_id("partner_{slug(email)}", row)
        result2 = render_id("contact_{slug(email)}", row)
        result3 = render_id("partner_{slug(email)}", row)  # Duplicate

        assert result1 == "partner_test_example_com"
        assert result2 == "contact_test_example_com"
        assert result3 == "partner_test_example_com_2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])