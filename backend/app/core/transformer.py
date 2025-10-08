"""
Transform library - data cleaning and normalization functions.
"""
import re
import phonenumbers
from typing import Any, Dict, Callable


class TransformRegistry:
    """Registry of transform functions that can be applied to column data."""

    def __init__(self):
        self.transforms: Dict[str, Callable] = {
            "trim": self.trim,
            "lower": self.lower,
            "upper": self.upper,
            "titlecase": self.titlecase,
            "phone_normalize": self.phone_normalize,
            "email_normalize": self.email_normalize,
            "currency_to_float": self.currency_to_float,
            "split_name": self.split_name,
            "concat": self.concat,
            "regex_extract": self.regex_extract,
        }

    def get(self, name: str) -> Callable:
        """Get a transform function by name."""
        return self.transforms.get(name)

    @staticmethod
    def trim(value: Any) -> str:
        """Trim whitespace from string."""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def lower(value: Any) -> str:
        """Convert to lowercase."""
        if value is None:
            return ""
        return str(value).lower()

    @staticmethod
    def upper(value: Any) -> str:
        """Convert to uppercase."""
        if value is None:
            return ""
        return str(value).upper()

    @staticmethod
    def titlecase(value: Any) -> str:
        """Convert to title case."""
        if value is None:
            return ""
        return str(value).title()

    @staticmethod
    def phone_normalize(value: Any, region: str = "US") -> str:
        """Normalize phone number to E.164 format."""
        if not value:
            return ""
        try:
            parsed = phonenumbers.parse(str(value), region)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return str(value)

    @staticmethod
    def email_normalize(value: Any) -> str:
        """Normalize email address (lowercase, trim)."""
        if not value:
            return ""
        email = str(value).strip().lower()
        # Basic validation
        if "@" not in email:
            return ""
        return email

    @staticmethod
    def currency_to_float(value: Any, currency_symbol: str = "$") -> float:
        """Parse currency string to float."""
        if not value:
            return 0.0
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(f"[{currency_symbol},\\s]", "", str(value))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def split_name(value: Any) -> Dict[str, str]:
        """Split full name into first and last name."""
        if not value:
            return {"first_name": "", "last_name": ""}
        parts = str(value).strip().split(maxsplit=1)
        return {
            "first_name": parts[0] if parts else "",
            "last_name": parts[1] if len(parts) > 1 else "",
        }

    @staticmethod
    def concat(*values: Any, separator: str = " ") -> str:
        """Concatenate multiple values."""
        return separator.join(str(v) for v in values if v)

    @staticmethod
    def regex_extract(value: Any, pattern: str, group: int = 0) -> str:
        """Extract text using regex pattern."""
        if not value:
            return ""
        match = re.search(pattern, str(value))
        if match:
            return match.group(group)
        return ""
