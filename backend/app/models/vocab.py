"""
Vocabulary resolution models for managing reference data policies.

Supports configurable resolution strategies per model and company context.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Index
from app.core.database import Base


class VocabPolicy(Base):
    """
    Defines vocabulary resolution policies for reference data models.

    Controls how to handle values that reference Odoo reference data
    (e.g., crm.stage, utm.source, res.country) during import.

    Resolution policies:
    - lookup_only: Only match existing records, fail if not found
    - create_if_missing: Create new records if lookup fails
    - suggest_only: Flag for manual review, don't auto-create
    """
    __tablename__ = "vocab_policies"

    id = Column(Integer, primary_key=True, index=True)

    # Model this policy applies to (e.g., "crm.stage", "utm.source")
    model = Column(String, nullable=False, index=True)

    # Company scope (nullable = global default)
    company_id = Column(Integer, nullable=True, index=True)

    # Default resolution strategy
    default_policy = Column(
        String,
        nullable=False,
        default="lookup_only"
    )  # lookup_only | create_if_missing | suggest_only

    # Company-specific overrides: {company_id: policy_str}
    company_overrides = Column(JSON, default=dict)

    # Whether creates require manual approval
    requires_approval = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Ensure one policy per (model, company_id) pair
    __table_args__ = (
        Index('ix_vocab_policy_model_company', 'model', 'company_id', unique=True),
    )


class VocabAlias(Base):
    """
    Alias mappings for fuzzy matching vocabulary values.

    Maps common variations/misspellings to canonical Odoo values.
    Example: "US", "USA", "United States" → "United States" (res.country)
    """
    __tablename__ = "vocab_aliases"

    id = Column(Integer, primary_key=True, index=True)

    # Model this alias applies to
    model = Column(String, nullable=False, index=True)

    # Field within the model (e.g., "name", "code")
    field = Column(String, nullable=False)

    # Alias (what user might type)
    alias = Column(String, nullable=False, index=True)

    # Canonical value (what exists in Odoo)
    canonical_value = Column(String, nullable=False)

    # Company scope (nullable = applies to all companies)
    company_id = Column(Integer, nullable=True, index=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Ensure aliases are unique per (model, field, alias, company_id)
    __table_args__ = (
        Index('ix_vocab_alias_lookup', 'model', 'field', 'alias', 'company_id', unique=True),
    )


class VocabCache(Base):
    """
    Caches Odoo vocabulary lookups to reduce API calls.

    Stores frequently accessed reference data with TTL.
    """
    __tablename__ = "vocab_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Model being cached
    model = Column(String, nullable=False, index=True)

    # Search key (normalized value used for lookup)
    search_key = Column(String, nullable=False, index=True)

    # Odoo record ID (null if not found)
    odoo_id = Column(Integer, nullable=True)

    # Full record data (JSON)
    record_data = Column(JSON, nullable=True)

    # Company scope
    company_id = Column(Integer, nullable=True, index=True)

    # Cache metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # TTL for cache invalidation

    # Ensure one cache entry per (model, search_key, company_id)
    __table_args__ = (
        Index('ix_vocab_cache_lookup', 'model', 'search_key', 'company_id', unique=True),
    )
