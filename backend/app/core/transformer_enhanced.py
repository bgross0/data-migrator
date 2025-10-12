"""
Enhanced Transform library - robust data cleaning and normalization.

This module provides improved versions of the transforms with better validation
and error handling.
"""
import re
import phonenumbers
from typing import Any, Dict, Callable, Optional


class EnhancedTransformRegistry:
    """Enhanced registry with robust validation and error handling."""

    def __init__(self):
        self.transforms: Dict[str, Callable] = {
            "trim": self.trim,
            "lower": self.lower,
            "upper": self.upper,
            "titlecase": self.titlecase,
            "phone_normalize": self.phone_normalize,
            "email_normalize": self.email_normalize,
            "email_validate": self.email_validate,
            "currency_to_float": self.currency_to_float,
            "split_name": self.split_name,
            "name_normalize": self.name_normalize,
            "concat": self.concat,
            "regex_extract": self.regex_extract,
        }

    def get(self, name: str) -> Callable:
        """Get a transform function by name."""
        return self.transforms.get(name)

    @staticmethod
    def trim(value: Any) -> str:
        """Trim whitespace from string."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
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
        """
        Normalize phone number to E.164 format.

        Handles:
        - US formats: (555) 123-4567, 555-123-4567, 555.123.4567, 5551234567
        - International: +86, +44, +1, etc.
        - Extensions: x123, ext. 45 (stripped)

        Returns:
            E.164 format (+15551234567) or original if parse fails
        """
        if not value:
            return ""
        try:
            # Strip extensions before parsing
            phone_str = str(value)
            # Remove common extension indicators
            phone_str = re.sub(r'\s*(x|ext\.?|extension)\s*\d+', '', phone_str, flags=re.IGNORECASE)

            parsed = phonenumbers.parse(phone_str, region)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return str(value)

    @staticmethod
    def email_normalize(value: Any) -> str:
        """
        Normalize and VALIDATE email address.

        Validation:
        - Must have exactly one @ symbol
        - Domain must have at least one dot (TLD required)
        - Must not have @@
        - Trims and lowercases

        Returns:
            Normalized email or empty string if invalid
        """
        if not value:
            return ""

        email = str(value).strip().lower()

        # Must have exactly one @
        if email.count('@') != 1:
            return ""  # Invalid: no @ or multiple @

        # Split into local and domain
        local, domain = email.split('@')

        # Local part must exist
        if not local:
            return ""

        # Domain must have a TLD (at least one dot)
        if '.' not in domain:
            return ""  # Invalid: no TLD (e.g., user@domain)

        # Domain must not be empty after @
        if not domain or domain == '.':
            return ""

        # Basic check: domain parts must exist
        domain_parts = domain.split('.')
        if any(not part for part in domain_parts):
            return ""  # Invalid: empty parts like user@domain. or user@.com

        return email

    @staticmethod
    def email_validate(value: Any) -> bool:
        """
        Validate if value is a valid email.

        Returns:
            True if valid email, False otherwise
        """
        if not value:
            return False

        email = str(value).strip().lower()

        # Must have exactly one @
        if email.count('@') != 1:
            return False

        # Split and check structure
        local, domain = email.split('@')

        if not local or not domain:
            return False

        if '.' not in domain:
            return False

        domain_parts = domain.split('.')
        if any(not part for part in domain_parts):
            return False

        return True

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
        """
        Split full name into first and last name.

        Handles:
        - "First Last" → {"first_name": "First", "last_name": "Last"}
        - "Last, First" → {"first_name": "First", "last_name": "Last"}
        - "Dr. First Last" → {"first_name": "First", "last_name": "Last"} (strips title)
        - "First Last Jr." → {"first_name": "First", "last_name": "Last Jr."}

        NOTE: This is a basic implementation. Complex names with multiple
        middle names or hyphenated names may not parse perfectly.
        """
        if not value:
            return {"first_name": "", "last_name": ""}

        name = str(value).strip()

        # Handle "Last, First" format
        if "," in name:
            parts = name.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""

            # Strip title from first name
            first_name = EnhancedTransformRegistry._strip_title(first_name)

            return {
                "first_name": first_name.title(),
                "last_name": last_name.title()
            }

        # Strip common titles
        name = EnhancedTransformRegistry._strip_title(name)

        # Split on first space
        parts = name.split(maxsplit=1)

        return {
            "first_name": parts[0].title() if parts else "",
            "last_name": parts[1].title() if len(parts) > 1 else ""
        }

    @staticmethod
    def _strip_title(name: str) -> str:
        """Strip common titles from name."""
        titles = [
            "Dr.", "Dr", "Mr.", "Mr", "Ms.", "Ms", "Mrs.", "Mrs",
            "Prof.", "Prof", "Rev.", "Rev", "Sr.", "Sr", "Jr.", "Jr"
        ]

        name = name.strip()
        for title in titles:
            if name.startswith(title):
                name = name[len(title):].strip()
                break

        return name

    @staticmethod
    def name_normalize(value: Any) -> str:
        """
        Comprehensive name normalization.

        - Handles "Last, First" → "First Last"
        - Strips titles (Dr., Mr., Ms., etc.)
        - Converts to Title Case
        - Trims whitespace

        Returns:
            Normalized name in "First Last" format
        """
        if not value:
            return ""

        split = EnhancedTransformRegistry.split_name(value)
        first = split["first_name"]
        last = split["last_name"]

        if first and last:
            return f"{first} {last}"
        elif first:
            return first
        elif last:
            return last
        else:
            return ""

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


# Import pandas for NaN checking
try:
    import pandas as pd
except ImportError:
    # If pandas not available, create a dummy module
    class pd:
        @staticmethod
        def isna(value):
            return value is None
