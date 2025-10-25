"""
Centralized Type System - Single source of truth for parsing and normalizing data types.

All data transformations MUST go through this registry to ensure consistency across:
- Column profiling
- Data cleaning
- Field matching
- Vocabulary resolution
- Import payload generation

This prevents bugs from inconsistent parsing (e.g., different phone parsers in different modules).
"""
import re
from typing import Any, Optional, Union, Dict
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import phonenumbers
from email_validator import validate_email, EmailNotValidError
import pycountry


class TypeParseError(Exception):
    """Raised when type parsing fails."""
    pass


class TypeRegistry:
    """
    Central registry of type parsers.

    Each parser:
    - Takes raw input (str, int, float, etc.)
    - Returns normalized, validated output
    - Raises TypeParseError on failure
    - Is idempotent (same input → same output)
    """

    # Supported date formats (tried in order)
    DATE_FORMATS = [
        '%Y-%m-%d',           # ISO: 2025-01-15
        '%Y/%m/%d',           # ISO with slashes
        '%m/%d/%Y',           # US: 01/15/2025
        '%d/%m/%Y',           # EU: 15/01/2025
        '%m-%d-%Y',           # US with dashes
        '%d-%m-%Y',           # EU with dashes
        '%Y%m%d',             # Compact: 20250115
        '%d %b %Y',           # 15 Jan 2025
        '%d %B %Y',           # 15 January 2025
        '%b %d, %Y',          # Jan 15, 2025
        '%B %d, %Y',          # January 15, 2025
    ]

    @staticmethod
    def parse_date(value: Any, hint: Optional[str] = None) -> Optional[date]:
        """
        Parse date from various formats.

        Args:
            value: Input value (str, datetime, date, int timestamp)
            hint: Optional format hint ('iso', 'us', 'eu')

        Returns:
            date object or None if empty

        Raises:
            TypeParseError: If value is not a valid date
        """
        if value is None or value == '':
            return None

        # Already a date/datetime
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        # Unix timestamp (int or str)
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value).date()
            except (ValueError, OSError):
                raise TypeParseError(f"Invalid timestamp: {value}")

        # String parsing
        value_str = str(value).strip()
        if not value_str:
            return None

        # Try all formats
        formats_to_try = TypeRegistry.DATE_FORMATS

        # Prioritize based on hint
        if hint == 'us':
            formats_to_try = ['%m/%d/%Y', '%m-%d-%Y'] + TypeRegistry.DATE_FORMATS
        elif hint == 'eu':
            formats_to_try = ['%d/%m/%Y', '%d-%m-%Y'] + TypeRegistry.DATE_FORMATS
        elif hint == 'iso':
            formats_to_try = ['%Y-%m-%d', '%Y/%m/%d'] + TypeRegistry.DATE_FORMATS

        for fmt in formats_to_try:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        raise TypeParseError(f"Could not parse date: {value}")

    @staticmethod
    def parse_decimal(value: Any, locale: str = 'en_US') -> Optional[Decimal]:
        """
        Parse decimal from string, handling locale-specific formatting.

        Args:
            value: Input value (str, int, float, Decimal)
            locale: Locale for decimal separator ('en_US', 'de_DE', 'fr_FR')
                   en_US: 1,234.56 (comma thousands, dot decimal)
                   de_DE: 1.234,56 (dot thousands, comma decimal)
                   fr_FR: 1 234,56 (space thousands, comma decimal)

        Returns:
            Decimal object or None if empty

        Raises:
            TypeParseError: If value is not a valid decimal
        """
        if value is None or value == '':
            return None

        # Already a Decimal
        if isinstance(value, Decimal):
            return value

        # Numeric types
        if isinstance(value, (int, float)):
            return Decimal(str(value))

        # String parsing
        value_str = str(value).strip()
        if not value_str:
            return None

        # Remove currency symbols and whitespace
        value_str = re.sub(r'[$€£¥₹]', '', value_str)
        value_str = value_str.replace(' ', '')

        # Handle locale-specific formats
        if locale in ['de_DE', 'fr_FR', 'es_ES', 'it_IT']:
            # European: dot = thousands, comma = decimal
            # Convert to US format: remove dots, replace comma with dot
            value_str = value_str.replace('.', '')
            value_str = value_str.replace(',', '.')
        else:
            # US/UK: comma = thousands, dot = decimal
            # Remove commas
            value_str = value_str.replace(',', '')

        try:
            return Decimal(value_str)
        except InvalidOperation:
            raise TypeParseError(f"Could not parse decimal: {value}")

    @staticmethod
    def parse_currency(value: Any, currency: str = 'USD', locale: str = 'en_US') -> Optional[Decimal]:
        """
        Parse currency amount, stripping symbols and normalizing.

        Args:
            value: Input value (str with currency symbol, number)
            currency: Currency code (USD, EUR, GBP, etc.) - for metadata only
            locale: Locale for decimal parsing

        Returns:
            Decimal amount or None if empty

        Raises:
            TypeParseError: If value is not valid currency
        """
        # Delegate to decimal parser (currency symbols already handled there)
        return TypeRegistry.parse_decimal(value, locale)

    @staticmethod
    def parse_phone(value: Any, default_region: str = 'US') -> Optional[str]:
        """
        Parse and normalize phone number to E.164 format.

        Args:
            value: Input phone (str, int)
            default_region: Default country code if not specified in number

        Returns:
            E.164 formatted phone (+15551234567) or None if empty

        Raises:
            TypeParseError: If phone is invalid
        """
        if value is None or value == '':
            return None

        value_str = str(value).strip()
        if not value_str:
            return None

        try:
            # Parse with default region
            parsed = phonenumbers.parse(value_str, default_region)

            # Validate
            if not phonenumbers.is_valid_number(parsed):
                raise TypeParseError(f"Invalid phone number: {value}")

            # Return E.164 format
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

        except phonenumbers.NumberParseException as e:
            raise TypeParseError(f"Could not parse phone: {value} - {e}")

    @staticmethod
    def parse_email(value: Any) -> Optional[str]:
        """
        Parse and normalize email address.

        Handles:
        - Lowercase normalization
        - Punycode (internationalized domains)
        - Whitespace stripping
        - Basic validation

        Args:
            value: Input email (str)

        Returns:
            Normalized email or None if empty

        Raises:
            TypeParseError: If email is invalid
        """
        if value is None or value == '':
            return None

        value_str = str(value).strip().lower()
        if not value_str:
            return None

        try:
            # Validate and normalize
            validated = validate_email(value_str, check_deliverability=False)
            return validated.normalized

        except EmailNotValidError as e:
            raise TypeParseError(f"Invalid email: {value} - {e}")

    @staticmethod
    def parse_country(value: Any, output_format: str = 'alpha_2') -> Optional[str]:
        """
        Parse country name/code to standard ISO format.

        Args:
            value: Country name or code (str)
                   Accepts: "United States", "US", "USA", "840"
            output_format: Output format:
                          'alpha_2': US
                          'alpha_3': USA
                          'numeric': 840
                          'name': United States

        Returns:
            Country code/name in requested format or None if empty

        Raises:
            TypeParseError: If country not found
        """
        if value is None or value == '':
            return None

        value_str = str(value).strip()
        if not value_str:
            return None

        try:
            # Try exact lookup by different fields
            country = None

            # Try alpha_2 (US, GB, DE)
            if len(value_str) == 2:
                country = pycountry.countries.get(alpha_2=value_str.upper())

            # Try alpha_3 (USA, GBR, DEU)
            if not country and len(value_str) == 3:
                country = pycountry.countries.get(alpha_3=value_str.upper())

            # Try numeric code (840, 826, 276)
            if not country and value_str.isdigit():
                country = pycountry.countries.get(numeric=value_str.zfill(3))

            # Try name lookup (fuzzy)
            if not country:
                # Exact name match
                country = pycountry.countries.get(name=value_str.title())

            # Fuzzy search if still not found
            if not country:
                results = pycountry.countries.search_fuzzy(value_str)
                if results:
                    country = results[0]

            if not country:
                raise TypeParseError(f"Country not found: {value}")

            # Return requested format
            if output_format == 'alpha_2':
                return country.alpha_2
            elif output_format == 'alpha_3':
                return country.alpha_3
            elif output_format == 'numeric':
                return country.numeric
            elif output_format == 'name':
                return country.name
            else:
                return country.alpha_2  # Default

        except (LookupError, AttributeError) as e:
            raise TypeParseError(f"Could not parse country: {value} - {e}")

    @staticmethod
    def parse_state(value: Any, country: str = 'US', output_format: str = 'code') -> Optional[str]:
        """
        Parse state/province to standard format.

        Args:
            value: State name or code (str)
                   Accepts: "California", "CA", "New York"
            country: Country code (for context)
            output_format: Output format:
                          'code': CA, NY
                          'name': California, New York

        Returns:
            State code/name in requested format or None if empty

        Raises:
            TypeParseError: If state not found
        """
        if value is None or value == '':
            return None

        value_str = str(value).strip()
        if not value_str:
            return None

        try:
            # Get subdivisions for country
            subdivisions = pycountry.subdivisions.get(country_code=country.upper())

            # Try exact code match (CA, NY)
            state = None
            for subdivision in subdivisions:
                # Code format is like "US-CA"
                state_code = subdivision.code.split('-')[1] if '-' in subdivision.code else subdivision.code

                if state_code == value_str.upper():
                    state = subdivision
                    break

            # Try name match
            if not state:
                for subdivision in subdivisions:
                    if subdivision.name.lower() == value_str.lower():
                        state = subdivision
                        break

            # Fuzzy match
            if not state:
                for subdivision in subdivisions:
                    if value_str.lower() in subdivision.name.lower():
                        state = subdivision
                        break

            if not state:
                raise TypeParseError(f"State not found: {value} in {country}")

            # Return requested format
            state_code = state.code.split('-')[1] if '-' in state.code else state.code

            if output_format == 'code':
                return state_code
            elif output_format == 'name':
                return state.name
            else:
                return state_code  # Default

        except (LookupError, AttributeError) as e:
            raise TypeParseError(f"Could not parse state: {value} - {e}")


# Singleton registry instance
type_registry = TypeRegistry()


# Convenience functions (use these in transforms)
def parse_date(value: Any, hint: Optional[str] = None) -> Optional[date]:
    """Parse date value."""
    return type_registry.parse_date(value, hint)


def parse_decimal(value: Any, locale: str = 'en_US') -> Optional[Decimal]:
    """Parse decimal value."""
    return type_registry.parse_decimal(value, locale)


def parse_currency(value: Any, currency: str = 'USD', locale: str = 'en_US') -> Optional[Decimal]:
    """Parse currency value."""
    return type_registry.parse_currency(value, currency, locale)


def parse_phone(value: Any, default_region: str = 'US') -> Optional[str]:
    """Parse phone number to E.164."""
    return type_registry.parse_phone(value, default_region)


def parse_email(value: Any) -> Optional[str]:
    """Parse and normalize email."""
    return type_registry.parse_email(value)


def parse_country(value: Any, output_format: str = 'alpha_2') -> Optional[str]:
    """Parse country to ISO code."""
    return type_registry.parse_country(value, output_format)


def parse_state(value: Any, country: str = 'US', output_format: str = 'code') -> Optional[str]:
    """Parse state/province code."""
    return type_registry.parse_state(value, country, output_format)
