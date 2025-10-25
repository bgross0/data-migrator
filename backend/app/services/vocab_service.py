"""
Controlled Vocabulary Resolution Service.

Enforces configurable per-entity policies for reference data resolution:
- lookup_only: Only match existing records, fail if not found
- create_if_missing: Create new records if lookup fails
- suggest_only: Flag for manual review, don't auto-create
"""
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import re

from app.models.vocab import VocabPolicy, VocabAlias, VocabCache
from app.connectors.odoo import OdooConnector


class VocabResolutionError(Exception):
    """Raised when vocab resolution fails."""
    pass


class VocabNormalization:
    """Normalization functions for vocabulary values."""

    @staticmethod
    def normalize(value: str) -> str:
        """
        Standard normalization: lowercase, trim, collapse spaces, remove punctuation.

        Args:
            value: Raw value to normalize

        Returns:
            Normalized string
        """
        if not value:
            return ""

        # Lowercase and trim
        normalized = value.lower().strip()

        # Remove common punctuation
        normalized = re.sub(r'[^\w\s-]', '', normalized)

        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """
        Normalize company name (remove legal suffixes).

        Args:
            name: Company name

        Returns:
            Normalized company name
        """
        normalized = VocabNormalization.normalize(name)

        # Remove legal suffixes
        suffixes = ['llc', 'inc', 'corp', 'ltd', 'limited', 'corporation', 'company', 'co']
        for suffix in suffixes:
            pattern = rf'\b{suffix}\b\.?$'
            normalized = re.sub(pattern, '', normalized).strip()

        return normalized

    @staticmethod
    def compute_dedupe_key(name: str, company_id: Optional[int] = None) -> str:
        """
        Compute dedupe key for vocabulary item.

        Args:
            name: Item name
            company_id: Company scope (None for global)

        Returns:
            Hash of normalized (name + company_id)
        """
        normalized = VocabNormalization.normalize(name)
        key_parts = [normalized]
        if company_id is not None:
            key_parts.append(str(company_id))

        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()


class ControlledVocabService:
    """
    Service for resolving vocabulary/reference data with configurable policies.

    Supports three resolution strategies:
    - lookup_only: Strict matching, fail if not found
    - create_if_missing: Create new record if lookup fails
    - suggest_only: Queue for manual review
    """

    def __init__(self, db: Session, odoo: Optional[OdooConnector] = None):
        """
        Initialize vocab service.

        Args:
            db: Database session
            odoo: Odoo connector (optional, for Odoo lookups)
        """
        self.db = db
        self.odoo = odoo
        self.cache_ttl_hours = 24  # Cache TTL

    def get_policy(self, model: str, company_id: Optional[int] = None) -> str:
        """
        Get resolution policy for a model.

        Args:
            model: Odoo model name (e.g., 'crm.stage')
            company_id: Company context (None for global)

        Returns:
            Policy string: 'lookup_only', 'create_if_missing', or 'suggest_only'
        """
        # Query for model-specific policy
        policy = self.db.query(VocabPolicy).filter(
            VocabPolicy.model == model,
            VocabPolicy.company_id == company_id
        ).first()

        if policy:
            # Check for company-specific override
            if company_id and policy.company_overrides:
                override = policy.company_overrides.get(str(company_id))
                if override:
                    return override

            return policy.default_policy

        # Default to lookup_only (safest)
        return 'lookup_only'

    def resolve_value(
        self,
        model: str,
        field: str,
        value: str,
        company_id: Optional[int] = None,
        policy_override: Optional[str] = None
    ) -> Tuple[Optional[int], str]:
        """
        Resolve a vocabulary value to an Odoo ID.

        Args:
            model: Odoo model (e.g., 'crm.stage')
            field: Field to match on (usually 'name')
            value: Value to resolve
            company_id: Company scope
            policy_override: Override default policy for this resolution

        Returns:
            Tuple of (odoo_id, action_taken)
            - odoo_id: Resolved Odoo ID (or None if not found)
            - action_taken: 'matched', 'created', 'quarantined'

        Raises:
            VocabResolutionError: If resolution fails and policy is lookup_only
        """
        if not value:
            return None, 'skipped'

        # Determine policy
        policy = policy_override or self.get_policy(model, company_id)

        # Normalize value
        normalized_value = VocabNormalization.normalize(value)
        search_key = VocabNormalization.compute_dedupe_key(value, company_id)

        # Step 1: Check cache
        cached = self._check_cache(model, search_key, company_id)
        if cached is not None:
            return cached, 'matched'

        # Step 2: Check alias table
        canonical = self._resolve_alias(model, field, value, company_id)
        if canonical:
            # Re-resolve with canonical value
            return self.resolve_value(model, field, canonical, company_id, policy_override)

        # Step 3: Lookup in Odoo (if connector available)
        if self.odoo:
            odoo_id = self._lookup_odoo(model, field, normalized_value, company_id)
            if odoo_id:
                # Cache the result
                self._update_cache(model, search_key, odoo_id, company_id)
                return odoo_id, 'matched'

        # Step 4: Apply policy (not found)
        if policy == 'lookup_only':
            # Strict mode: fail
            raise VocabResolutionError(
                f"Vocab lookup failed for {model}.{field}='{value}' (company_id={company_id}). "
                f"Policy is 'lookup_only'."
            )

        elif policy == 'create_if_missing':
            # Create new record in Odoo
            if not self.odoo:
                raise VocabResolutionError(
                    f"Cannot create {model} record - Odoo connector not available"
                )

            odoo_id = self._create_odoo(model, {field: value}, company_id)

            # Cache the new record
            self._update_cache(model, search_key, odoo_id, company_id)

            return odoo_id, 'created'

        elif policy == 'suggest_only':
            # Queue for manual review (quarantine)
            return None, 'quarantined'

        else:
            raise ValueError(f"Unknown policy: {policy}")

    def _check_cache(
        self,
        model: str,
        search_key: str,
        company_id: Optional[int]
    ) -> Optional[int]:
        """
        Check vocab cache for existing resolution.

        Args:
            model: Odoo model
            search_key: Normalized search key
            company_id: Company scope

        Returns:
            Cached Odoo ID or None
        """
        cache_entry = self.db.query(VocabCache).filter(
            VocabCache.model == model,
            VocabCache.search_key == search_key,
            VocabCache.company_id == company_id
        ).first()

        if cache_entry:
            # Check expiration
            if cache_entry.expires_at and cache_entry.expires_at < datetime.utcnow():
                # Expired, delete
                self.db.delete(cache_entry)
                self.db.commit()
                return None

            return cache_entry.odoo_id

        return None

    def _update_cache(
        self,
        model: str,
        search_key: str,
        odoo_id: int,
        company_id: Optional[int],
        record_data: Optional[Dict[str, Any]] = None
    ):
        """
        Update vocab cache with resolved value.

        Args:
            model: Odoo model
            search_key: Normalized search key
            odoo_id: Resolved Odoo ID
            company_id: Company scope
            record_data: Full Odoo record data (optional)
        """
        # Upsert cache entry
        cache_entry = self.db.query(VocabCache).filter(
            VocabCache.model == model,
            VocabCache.search_key == search_key,
            VocabCache.company_id == company_id
        ).first()

        if cache_entry:
            # Update existing
            cache_entry.odoo_id = odoo_id
            cache_entry.record_data = record_data
            cache_entry.created_at = datetime.utcnow()
            cache_entry.expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
        else:
            # Create new
            cache_entry = VocabCache(
                model=model,
                search_key=search_key,
                odoo_id=odoo_id,
                record_data=record_data,
                company_id=company_id,
                expires_at=datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
            )
            self.db.add(cache_entry)

        self.db.commit()

    def _resolve_alias(
        self,
        model: str,
        field: str,
        value: str,
        company_id: Optional[int]
    ) -> Optional[str]:
        """
        Check if value has a known alias mapping.

        Args:
            model: Odoo model
            field: Field name
            value: Value to check
            company_id: Company scope

        Returns:
            Canonical value if alias found, else None
        """
        normalized = VocabNormalization.normalize(value)

        alias = self.db.query(VocabAlias).filter(
            VocabAlias.model == model,
            VocabAlias.field == field,
            VocabAlias.alias == normalized,
            VocabAlias.company_id.in_([company_id, None])  # Check both company-specific and global
        ).first()

        if alias:
            return alias.canonical_value

        return None

    def _lookup_odoo(
        self,
        model: str,
        field: str,
        value: str,
        company_id: Optional[int]
    ) -> Optional[int]:
        """
        Lookup record in Odoo by field value.

        Args:
            model: Odoo model
            field: Field to search on
            value: Value to match
            company_id: Company scope

        Returns:
            Odoo ID if found, else None
        """
        if not self.odoo:
            return None

        # Build search domain
        domain = [[field, '=ilike', value]]  # Case-insensitive match

        # Add company_id filter if model supports it
        if company_id and model not in ['res.country', 'res.country.state']:
            domain.append(['company_id', '=', company_id])

        # Search in Odoo
        records = self.odoo.search_read(
            model,
            domain=domain,
            fields=['id', field],
            limit=1
        )

        if records:
            return records[0]['id']

        return None

    def _create_odoo(
        self,
        model: str,
        values: Dict[str, Any],
        company_id: Optional[int]
    ) -> int:
        """
        Create new record in Odoo.

        Args:
            model: Odoo model
            values: Field values
            company_id: Company scope

        Returns:
            Created Odoo ID
        """
        if not self.odoo:
            raise VocabResolutionError("Odoo connector not available")

        # Add company_id if model supports it
        if company_id and model not in ['res.country', 'res.country.state']:
            values['company_id'] = company_id

        # Create in Odoo
        odoo_id = self.odoo.create(model, values)

        return odoo_id

    def add_alias(
        self,
        model: str,
        field: str,
        alias: str,
        canonical_value: str,
        company_id: Optional[int] = None
    ):
        """
        Add alias mapping to database.

        Args:
            model: Odoo model
            field: Field name
            alias: Alias value (will be normalized)
            canonical_value: Canonical value to resolve to
            company_id: Company scope (None for global)
        """
        normalized_alias = VocabNormalization.normalize(alias)

        # Check if alias already exists
        existing = self.db.query(VocabAlias).filter(
            VocabAlias.model == model,
            VocabAlias.field == field,
            VocabAlias.alias == normalized_alias,
            VocabAlias.company_id == company_id
        ).first()

        if existing:
            # Update canonical value
            existing.canonical_value = canonical_value
        else:
            # Create new alias
            alias_entry = VocabAlias(
                model=model,
                field=field,
                alias=normalized_alias,
                canonical_value=canonical_value,
                company_id=company_id
            )
            self.db.add(alias_entry)

        self.db.commit()

    def seed_default_aliases(self):
        """Seed common alias mappings."""

        # Country aliases
        country_aliases = [
            ('res.country', 'name', 'US', 'United States'),
            ('res.country', 'name', 'USA', 'United States'),
            ('res.country', 'name', 'UK', 'United Kingdom'),
            ('res.country', 'name', 'GB', 'United Kingdom'),
        ]

        # UTM source aliases
        utm_source_aliases = [
            ('utm.source', 'name', 'G Ads', 'google'),
            ('utm.source', 'name', 'Gooogle', 'google'),
            ('utm.source', 'name', 'FB', 'facebook'),
            ('utm.source', 'name', 'LI', 'linkedin'),
        ]

        # Seed all aliases
        for model, field, alias, canonical in country_aliases + utm_source_aliases:
            self.add_alias(model, field, alias, canonical, company_id=None)
