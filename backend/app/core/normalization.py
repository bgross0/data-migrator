"""
Normalization functions for entity resolution and deduplication.

All normalization logic centralized here for consistency across:
- Identity resolution
- Natural key generation
- Vocabulary matching
- Deduplication
"""
import re
import hashlib
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta


class Normalizer:
    """Centralized normalization functions."""

    @staticmethod
    def normalize_string(value: Optional[str]) -> str:
        """
        Standard string normalization.

        - Lowercase
        - Trim whitespace
        - Collapse multiple spaces to single
        - Remove common punctuation

        Args:
            value: Raw string

        Returns:
            Normalized string (empty string if None)
        """
        if not value:
            return ""

        # Lowercase and strip
        normalized = value.lower().strip()

        # Remove punctuation (keep hyphens and underscores)
        normalized = re.sub(r'[^\w\s-]', '', normalized)

        # Collapse spaces
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    @staticmethod
    def normalize_company_name(name: Optional[str]) -> str:
        """
        Normalize company name - remove legal suffixes.

        Args:
            name: Company name

        Returns:
            Normalized company name
        """
        normalized = Normalizer.normalize_string(name)

        # Remove common legal suffixes
        suffixes = [
            'llc', 'inc', 'corp', 'ltd', 'limited', 'corporation',
            'company', 'co', 'incorporated', 'l l c', 'l l p'
        ]

        for suffix in suffixes:
            # Match suffix at end of string (with optional period)
            pattern = rf'\b{suffix}\.?$'
            normalized = re.sub(pattern, '', normalized).strip()

        return normalized

    @staticmethod
    def normalize_vat(vat: Optional[str]) -> str:
        """
        Normalize VAT number.

        - Remove spaces, dashes, dots
        - Uppercase

        Args:
            vat: VAT number

        Returns:
            Normalized VAT
        """
        if not vat:
            return ""

        # Remove separators
        normalized = re.sub(r'[\s\-\.]', '', vat)

        # Uppercase
        normalized = normalized.upper()

        return normalized

    @staticmethod
    def extract_email_domain(email: Optional[str]) -> str:
        """
        Extract domain from email address.

        Args:
            email: Email address

        Returns:
            Domain (e.g., "example.com") or empty string
        """
        if not email or '@' not in email:
            return ""

        return email.split('@')[1].lower().strip()

    @staticmethod
    def normalize_address(
        street: Optional[str] = None,
        street2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> str:
        """
        Normalize full address to single string.

        Args:
            street: Street address
            street2: Street address line 2
            city: City
            state: State/province
            country: Country
            zip_code: Postal code

        Returns:
            Normalized address string (components joined with |)
        """
        components = []

        if street:
            components.append(Normalizer.normalize_string(street))
        if street2:
            components.append(Normalizer.normalize_string(street2))
        if city:
            components.append(Normalizer.normalize_string(city))
        if state:
            components.append(Normalizer.normalize_string(state))
        if country:
            components.append(Normalizer.normalize_string(country))
        if zip_code:
            # Remove spaces from zip
            components.append(re.sub(r'\s', '', zip_code).upper())

        return '|'.join(components)

    @staticmethod
    def date_bucket(dt: date, days: int = 3) -> date:
        """
        Bucket date to N-day window (for fuzzy date matching).

        Returns the Monday of the week containing the date.

        Args:
            dt: Date to bucket
            days: Window size (not used, kept for interface compatibility)

        Returns:
            Monday of the week
        """
        # Get Monday of the week (weekday 0 = Monday)
        return dt - timedelta(days=dt.weekday())


class NaturalKeyGenerator:
    """Generate natural keys for deduplication."""

    @staticmethod
    def generate_partner_company_key(
        vat: Optional[str] = None,
        name: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state_code: Optional[str] = None,
        country_code: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> str:
        """
        Generate natural key for company partner.

        Priority:
        1. VAT (if present)
        2. Name + Address
        3. Name + Phone/Email domain

        Args:
            vat: VAT number
            name: Company name
            street: Street address
            city: City
            state_code: State code
            country_code: Country code
            phone: Phone number
            email: Email address

        Returns:
            MD5 hash of natural key components
        """
        # Priority 1: VAT
        if vat:
            normalized_vat = Normalizer.normalize_vat(vat)
            if normalized_vat:
                return hashlib.md5(f"vat:{normalized_vat}".encode()).hexdigest()

        # Priority 2: Name + Address
        if name and (street or city):
            normalized_name = Normalizer.normalize_company_name(name)
            address = Normalizer.normalize_address(street, None, city, state_code, country_code)
            key = f"name_addr:{normalized_name}|{address}"
            return hashlib.md5(key.encode()).hexdigest()

        # Priority 3: Name + Contact info
        if name and (phone or email):
            normalized_name = Normalizer.normalize_company_name(name)
            contact = phone if phone else Normalizer.extract_email_domain(email)
            key = f"name_contact:{normalized_name}|{contact}"
            return hashlib.md5(key.encode()).hexdigest()

        # Fallback: hash all available fields
        all_fields = f"{name}|{street}|{city}|{phone}|{email}"
        return hashlib.md5(all_fields.encode()).hexdigest()

    @staticmethod
    def generate_partner_contact_key(
        parent_id: int,
        full_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> str:
        """
        Generate natural key for contact (person).

        Key: parent_id + full_name + (email OR phone)

        Args:
            parent_id: Parent company ID
            full_name: Full name
            email: Email address
            phone: Phone number

        Returns:
            MD5 hash of natural key
        """
        normalized_name = Normalizer.normalize_string(full_name)
        contact = email if email else phone if phone else ""

        key = f"contact:{parent_id}|{normalized_name}|{contact}"
        return hashlib.md5(key.encode()).hexdigest()

    @staticmethod
    def generate_lead_key(
        external_id: Optional[str] = None,
        partner_id: Optional[int] = None,
        name: Optional[str] = None,
        email_from: Optional[str] = None,
        create_date: Optional[date] = None
    ) -> str:
        """
        Generate natural key for CRM lead.

        Priority:
        1. External ID
        2. Partner + Name + Date bucket
        3. Email + Name + Date bucket

        Args:
            external_id: External ID from source system
            partner_id: Partner ID
            name: Lead name
            email_from: Email address
            create_date: Creation date

        Returns:
            MD5 hash of natural key
        """
        # Priority 1: External ID
        if external_id:
            return hashlib.md5(f"ext_id:{external_id}".encode()).hexdigest()

        # Priority 2: Partner + Name + Date
        if partner_id and name and create_date:
            normalized_name = Normalizer.normalize_string(name)
            date_bucket = Normalizer.date_bucket(create_date)
            key = f"partner_name_date:{partner_id}|{normalized_name}|{date_bucket}"
            return hashlib.md5(key.encode()).hexdigest()

        # Priority 3: Email + Name + Date
        if email_from and name and create_date:
            normalized_name = Normalizer.normalize_string(name)
            normalized_email = email_from.lower().strip()
            date_bucket = Normalizer.date_bucket(create_date)
            key = f"email_name_date:{normalized_email}|{normalized_name}|{date_bucket}"
            return hashlib.md5(key.encode()).hexdigest()

        # Fallback
        all_fields = f"{partner_id}|{name}|{email_from}|{create_date}"
        return hashlib.md5(all_fields.encode()).hexdigest()

    @staticmethod
    def generate_vocab_key(
        name: str,
        company_id: Optional[int] = None
    ) -> str:
        """
        Generate natural key for vocabulary item.

        Key: normalized_name + company_id

        Args:
            name: Item name
            company_id: Company scope (None for global)

        Returns:
            MD5 hash of natural key
        """
        normalized = Normalizer.normalize_string(name)
        key = f"vocab:{normalized}|{company_id if company_id else 'global'}"
        return hashlib.md5(key.encode()).hexdigest()


class ContentHasher:
    """Generate content hashes for change detection."""

    @staticmethod
    def hash_record(record: Dict[str, Any], exclude_fields: Optional[List[str]] = None) -> str:
        """
        Generate content hash for a record.

        Hashes all field values in deterministic order (sorted keys).
        Excludes metadata fields like created_at, updated_at by default.

        Args:
            record: Record dictionary
            exclude_fields: Fields to exclude from hash

        Returns:
            MD5 hash of record content
        """
        if exclude_fields is None:
            exclude_fields = [
                'id', 'created_at', 'updated_at', 'create_date', 'write_date',
                '__last_update', 'display_name'
            ]

        # Filter and sort keys
        filtered = {
            k: v for k, v in record.items()
            if k not in exclude_fields and v is not None
        }

        # Sort by key for deterministic order
        sorted_items = sorted(filtered.items())

        # Build hash string
        hash_parts = []
        for key, value in sorted_items:
            # Convert lists to sorted tuples for m2m fields
            if isinstance(value, list):
                value = tuple(sorted(str(v) for v in value))

            hash_parts.append(f"{key}:{value}")

        hash_string = '|'.join(hash_parts)
        return hashlib.md5(hash_string.encode()).hexdigest()

    @staticmethod
    def hash_relationship_values(values: List[Any]) -> str:
        """
        Hash list of related values (for m2m/o2m fields).

        Sorted to ensure deterministic hash regardless of order.

        Args:
            values: List of IDs or values

        Returns:
            MD5 hash of sorted values
        """
        sorted_values = sorted(str(v) for v in values)
        hash_string = ','.join(sorted_values)
        return hashlib.md5(hash_string.encode()).hexdigest()
