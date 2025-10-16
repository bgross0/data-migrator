"""
Idempotent normalizers for data cleaning at emit-time.

All normalizers must be idempotent: normalized(normalized(x)) == normalized(x)
Applied only once during CSV emission, never double-normalized.

Key principle: These are final, emit-time transforms.
The data_cleaner.py does initial cleaning, these do final normalization.
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any
import phonenumbers
from email_validator import validate_email, EmailNotValidError


class NormalizeError(Exception):
    """Raised when normalization fails and cannot be recovered."""

    pass


def normalize_phone_us(value: Optional[str]) -> str:
    """
    Normalize US phone number to "1XXXXXXXXXX" format.

    Rules:
    - Strip all non-digits
    - If 10 digits → prefix with 1 → "1XXXXXXXXXX"
    - If 11 digits starting with 1 → keep as is
    - Otherwise → raise NormalizeError

    Idempotent: normalize_phone_us("15551234567") == "15551234567"

    Args:
        value: Phone number string (may include formatting)

    Returns:
        Normalized phone: "1XXXXXXXXXX" (11 digits)

    Raises:
        NormalizeError: If phone cannot be normalized to valid US format
    """
    if not value:
        raise NormalizeError("Phone number is empty or None")

    # Strip all non-digits
    digits = re.sub(r"\D", "", str(value))

    if len(digits) == 10:
        # Standard US format without country code
        return f"1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        # Already has country code
        return digits
    else:
        raise NormalizeError(
            f"Invalid US phone format: expected 10 or 11 digits, got {len(digits)} ({value})"
        )


def normalize_email(value: Optional[str]) -> str:
    """
    Normalize email address to lowercase with validation.

    Rules:
    - Strip whitespace
    - Convert to lowercase
    - Validate email format (basic check)

    Idempotent: normalize_email("USER@EXAMPLE.COM") == "user@example.com"

    Args:
        value: Email address string

    Returns:
        Normalized email (lowercase, trimmed)

    Raises:
        NormalizeError: If email is invalid
    """
    if not value:
        raise NormalizeError("Email is empty or None")

    email = str(value).strip().lower()

    # Basic validation
    if "@" not in email or "." not in email.split("@")[1]:
        raise NormalizeError(f"Invalid email format: {value}")

    try:
        # Use email-validator for more robust validation
        validated = validate_email(email, check_deliverability=False)
        return validated.normalized
    except EmailNotValidError as e:
        raise NormalizeError(f"Invalid email: {e}")


def normalize_date_any(value: Optional[str]) -> str:
    """
    Normalize date to ISO format "YYYY-MM-DD".

    Tries multiple date formats:
    - ISO: YYYY-MM-DD
    - US: mm/dd/yyyy, mm-dd-yyyy
    - EU: dd/mm/yyyy, dd-mm-yyyy
    - Alternative: YYYY/MM/DD
    - Named months: "Jan 15, 2024", "15 Jan 2024"

    Idempotent: normalize_date_any("2024-01-15") == "2024-01-15"

    Args:
        value: Date string in various formats

    Returns:
        ISO date string "YYYY-MM-DD"

    Raises:
        NormalizeError: If date cannot be parsed
    """
    if not value:
        raise NormalizeError("Date is empty or None")

    value_str = str(value).strip()

    # If already in ISO format and valid, return as-is (idempotency)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value_str):
        try:
            datetime.strptime(value_str, "%Y-%m-%d")
            return value_str
        except ValueError:
            pass  # Invalid date, continue trying other formats

    # Try common formats
    formats = [
        "%Y-%m-%d",  # ISO
        "%m/%d/%Y",  # US: 01/15/2024
        "%d/%m/%Y",  # EU: 15/01/2024
        "%m-%d-%Y",  # US: 01-15-2024
        "%d-%m-%Y",  # EU: 15-01-2024
        "%Y/%m/%d",  # Alternative: 2024/01/15
        "%b %d, %Y",  # Jan 15, 2024
        "%B %d, %Y",  # January 15, 2024
        "%d %b %Y",  # 15 Jan 2024
        "%d %B %Y",  # 15 January 2024
        "%Y%m%d",  # Compact: 20240115
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(value_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try Excel serial date (days since 1899-12-30)
    try:
        serial = float(value_str)
        if 1 < serial < 100000:  # Reasonable range for Excel dates
            # Excel epoch is 1899-12-30
            excel_epoch = datetime(1899, 12, 30)
            from datetime import timedelta

            parsed = excel_epoch + timedelta(days=serial)
            return parsed.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        pass

    raise NormalizeError(f"Cannot parse date: {value}")


def coerce_bool(value: Optional[Any]) -> str:
    """
    Coerce value to boolean string "true" or "false".

    Recognizes:
    - Truthy: yes, y, true, t, 1, True
    - Falsy: no, n, false, f, 0, False, empty

    Idempotent: coerce_bool("true") == "true"

    Args:
        value: Value to coerce to boolean

    Returns:
        "true" or "false"

    Raises:
        NormalizeError: If value cannot be interpreted as boolean
    """
    if value is None or value == "":
        raise NormalizeError("Boolean value is empty or None")

    # Handle boolean type
    if isinstance(value, bool):
        return "true" if value else "false"

    # Handle string
    val_str = str(value).lower().strip()

    # Already normalized (idempotency)
    if val_str == "true":
        return "true"
    if val_str == "false":
        return "false"

    # Truthy values
    if val_str in ["yes", "y", "t", "1"]:
        return "true"

    # Falsy values
    if val_str in ["no", "n", "f", "0"]:
        return "false"

    raise NormalizeError(f"Cannot coerce to boolean: {value}")


def coerce_enum(
    value: Optional[str],
    mapping: Optional[Dict[str, str]],
    synonyms_map: Optional[Dict[str, str]],
) -> str:
    """
    Coerce enum value using mapping and synonyms.

    Resolution order:
    1. Check synonyms_map (aliases → canonical)
    2. Check mapping keys (source values → external IDs)
    3. Check mapping values (already an external ID)

    Idempotent: coerce_enum("stage_won", ...) == "stage_won"

    Args:
        value: Raw enum value from source data
        mapping: Optional inline mapping {source_value: external_id}
        synonyms_map: Optional seed synonyms {alias: canonical_external_id}

    Returns:
        Canonical external ID

    Raises:
        NormalizeError: If value cannot be resolved
    """
    if not value:
        raise NormalizeError("Enum value is empty or None")

    value_str = str(value).strip()

    # 1. Check synonyms first (seed-based resolution)
    if synonyms_map and value_str in synonyms_map:
        return synonyms_map[value_str]

    # 2. Check inline mapping keys
    if mapping and value_str in mapping:
        return mapping[value_str]

    # 3. Check if already an external ID (in mapping values or synonyms values)
    if mapping and value_str in mapping.values():
        # Already normalized
        return value_str

    if synonyms_map and value_str in synonyms_map.values():
        # Already canonical
        return value_str

    raise NormalizeError(
        f"Unknown enum value: '{value_str}' (not in mapping or synonyms)"
    )


# Helper: Test idempotency
def _test_idempotency():
    """
    Internal test to verify all normalizers are idempotent.
    Run during development to ensure invariants hold.
    """
    # Phone
    assert normalize_phone_us("15551234567") == "15551234567"
    assert normalize_phone_us("(555) 123-4567") == "15551234567"

    # Email
    assert normalize_email("user@example.com") == "user@example.com"
    assert normalize_email("USER@EXAMPLE.COM") == "user@example.com"

    # Date
    assert normalize_date_any("2024-01-15") == "2024-01-15"
    assert normalize_date_any("01/15/2024") == "2024-01-15"

    # Bool
    assert coerce_bool("true") == "true"
    assert coerce_bool("false") == "false"
    assert coerce_bool("yes") == "true"

    # Enum
    mapping = {"lead": "lead", "opp": "opportunity"}
    synonyms = {"opportunity": "opportunity"}
    assert coerce_enum("opportunity", mapping, synonyms) == "opportunity"
    assert coerce_enum("lead", mapping, synonyms) == "lead"

    print("✓ All normalizers are idempotent")


if __name__ == "__main__":
    _test_idempotency()
