"""
Import Ledger Model.

Tracks all imported records with complete lineage from source to Odoo.
Enables idempotency, replay prevention, and cross-source deduplication.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class ImportLedger(Base):
    """
    Comprehensive import tracking for idempotency and lineage.

    Records the mapping from source records to Odoo records with:
    - Source identity (src_system, src_table, src_pk)
    - Natural key hash for deduplication
    - Content hash for change detection
    - Odoo mapping (odoo_model, odoo_id, external_id)
    - Resolution metadata (matched vs created, confidence)
    """
    __tablename__ = "import_ledger"

    id = Column(Integer, primary_key=True, index=True)

    # Run tracking
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    batch_id = Column(String, nullable=False)  # Logical batch identifier

    # Source identity (where did this come from?)
    src_system = Column(String, nullable=False)  # 'hubspot', 'salesforce', 'csv_import_2024'
    src_table = Column(String, nullable=False)   # 'leads', 'contacts', 'companies'
    src_pk = Column(String, nullable=False)      # Source record primary key
    src_hash = Column(String, nullable=False)    # MD5 of raw source data

    # Canonical identity (how do we dedupe?)
    natural_key_hash = Column(String, nullable=False)  # Hash of natural key components
    content_hash = Column(String, nullable=False)      # Hash of business attributes

    # Odoo mapping (where did it go in Odoo?)
    odoo_model = Column(String, nullable=False)  # 'res.partner', 'crm.lead', etc.
    odoo_id = Column(Integer, nullable=True)     # Odoo internal ID (NULL if not yet loaded)
    external_id = Column(String, nullable=True)  # Odoo external_id (XMLID)

    # Resolution metadata (how was it resolved?)
    resolution_action = Column(String, nullable=False)  # 'matched', 'created', 'updated', 'skipped', 'quarantined'
    match_confidence = Column(Float, nullable=True)     # Similarity score for fuzzy matches (0.0-1.0)
    match_method = Column(String, nullable=True)        # 'exact', 'fuzzy', 'manual', 'alias'

    # Decision log (why was this decision made?)
    decision_log = Column(JSON, nullable=True)  # {rationale, candidates, user_override, etc.}

    # FK resolution version (which FK map was used?)
    fk_map_version = Column(String, nullable=True)  # Hash/version of FK resolution state

    # Quarantine tracking
    quarantine_reason = Column(String, nullable=True)  # If resolution_action='quarantined'
    quarantine_resolved_at = Column(DateTime, nullable=True)
    quarantine_resolved_by = Column(String, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    run = relationship("Run", back_populates="ledger_entries")

    # Indexes for fast lookups
    __table_args__ = (
        # Source identity lookup (idempotency check)
        Index('idx_ledger_source', 'src_system', 'src_table', 'src_pk'),

        # Natural key lookup (deduplication)
        Index('idx_ledger_natural_key', 'odoo_model', 'natural_key_hash'),

        # Content hash lookup (change detection)
        Index('idx_ledger_content', 'odoo_model', 'content_hash'),

        # Odoo mapping lookup (reverse lookup)
        Index('idx_ledger_odoo', 'odoo_model', 'odoo_id'),

        # External ID lookup
        Index('idx_ledger_external_id', 'external_id'),

        # Run + batch lookup (batch queries)
        Index('idx_ledger_run_batch', 'run_id', 'batch_id'),

        # Quarantine queue lookup
        Index('idx_ledger_quarantine', 'resolution_action', 'quarantine_resolved_at'),
    )


class ImportDecision(Base):
    """
    HITL decision log for ambiguous matches.

    When identity resolution cannot auto-match (multi-match, low confidence),
    records are quarantined and await manual review. This table tracks
    the human decision and rationale.
    """
    __tablename__ = "import_decisions"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to ledger entry
    ledger_id = Column(Integer, ForeignKey("import_ledger.id"), nullable=False)

    # Source record data (for display in HITL UI)
    source_data = Column(JSON, nullable=False)

    # Match candidates presented to user
    candidates = Column(JSON, nullable=False)  # [{partner_sk, score, name, ...}, ...]

    # Decision made
    decision_type = Column(String, nullable=False)  # 'match_to_candidate', 'create_new', 'skip', 'merge'
    selected_candidate_id = Column(Integer, nullable=True)  # If decision_type='match_to_candidate'

    # Rationale
    rationale = Column(String, nullable=True)  # Free text explanation

    # Audit
    decided_by = Column(String, nullable=False)  # User email/ID
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ledger_entry = relationship("ImportLedger")

    __table_args__ = (
        Index('idx_decision_ledger', 'ledger_id'),
        Index('idx_decision_decided_by', 'decided_by'),
    )
