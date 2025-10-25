"""
Quarantine Service.

Manages quarantined records that require manual review before import.

Quarantine scenarios:
1. Multi-match collisions (identity resolution ambiguity)
2. Validation failures (business rule violations)
3. Missing required foreign keys
4. Data quality issues (out-of-range values, suspicious patterns)
5. Vocab resolution failures (lookup_only policy violated)
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.ledger import ImportLedger, ImportDecision
from app.services.collision_handler import CollisionHandler, CollisionResolution


class QuarantineReason:
    """Enumeration of quarantine reasons."""
    MULTI_MATCH = "multi_match"
    VALIDATION_FAILED = "validation_failed"
    MISSING_FK = "missing_foreign_key"
    DATA_QUALITY = "data_quality_issue"
    VOCAB_FAILED = "vocab_resolution_failed"
    POLYMORPHIC_AMBIGUOUS = "polymorphic_ambiguous"


class QuarantineService:
    """
    Service for managing quarantined records.

    Provides unified interface for quarantining, reviewing, and resolving
    records that cannot be auto-imported.
    """

    def __init__(self, db: Session):
        """
        Initialize quarantine service.

        Args:
            db: Database session
        """
        self.db = db
        self.collision_handler = CollisionHandler(db)

    def quarantine_record(
        self,
        source_record: Dict[str, Any],
        odoo_model: str,
        run_id: int,
        batch_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ) -> ImportLedger:
        """
        Quarantine a record for manual review.

        Args:
            source_record: Source data
            odoo_model: Target Odoo model
            run_id: Current run ID
            batch_id: Current batch ID
            reason: Quarantine reason (from QuarantineReason)
            details: Additional details (candidates, validation errors, etc.)

        Returns:
            Created ImportLedger entry with quarantine status
        """
        ledger_entry = ImportLedger(
            run_id=run_id,
            batch_id=batch_id,
            src_system=source_record.get('src_system', 'unknown'),
            src_table=source_record.get('src_table', 'unknown'),
            src_pk=source_record.get('src_pk', 'unknown'),
            src_hash=source_record.get('src_hash', ''),
            natural_key_hash=source_record.get('natural_key_hash', ''),
            content_hash=source_record.get('content_hash', ''),
            odoo_model=odoo_model,
            odoo_id=None,
            external_id=None,
            resolution_action='quarantined',
            match_confidence=None,
            match_method=reason,
            decision_log=details or {},
            quarantine_reason=reason,
            quarantine_resolved_at=None,
            quarantine_resolved_by=None,
        )

        self.db.add(ledger_entry)
        self.db.commit()
        self.db.refresh(ledger_entry)

        return ledger_entry

    def get_quarantine_queue(
        self,
        run_id: Optional[int] = None,
        reason: Optional[str] = None,
        odoo_model: Optional[str] = None,
        resolved: bool = False,
        limit: int = 50
    ) -> List[ImportLedger]:
        """
        Get quarantined records for review.

        Args:
            run_id: Filter by run ID
            reason: Filter by quarantine reason
            odoo_model: Filter by Odoo model
            resolved: Include resolved records (default: False)
            limit: Maximum records to return

        Returns:
            List of quarantined ImportLedger entries
        """
        query = self.db.query(ImportLedger).filter(
            ImportLedger.resolution_action == 'quarantined'
        )

        if not resolved:
            query = query.filter(ImportLedger.quarantine_resolved_at.is_(None))

        if run_id:
            query = query.filter(ImportLedger.run_id == run_id)

        if reason:
            query = query.filter(ImportLedger.quarantine_reason == reason)

        if odoo_model:
            query = query.filter(ImportLedger.odoo_model == odoo_model)

        query = query.order_by(ImportLedger.created_at.desc()).limit(limit)

        return query.all()

    def resolve_quarantine(
        self,
        ledger_id: int,
        action: str,
        decided_by: str,
        rationale: Optional[str] = None,
        resolution_data: Optional[Dict[str, Any]] = None
    ) -> ImportLedger:
        """
        Resolve quarantined record.

        Args:
            ledger_id: ImportLedger ID
            action: Resolution action ('approve', 'reject', 'fix', 'match_to_candidate')
            decided_by: User email/ID
            rationale: Explanation
            resolution_data: Additional resolution data (e.g., fixed values, selected candidate)

        Returns:
            Updated ImportLedger entry
        """
        ledger_entry = self.db.query(ImportLedger).filter(
            ImportLedger.id == ledger_id
        ).first()

        if not ledger_entry:
            raise ValueError(f"Ledger entry {ledger_id} not found")

        if ledger_entry.resolution_action != 'quarantined':
            raise ValueError(f"Ledger entry {ledger_id} is not quarantined")

        # Create decision record
        decision = ImportDecision(
            ledger_id=ledger_id,
            source_data=self._extract_source_data(ledger_entry),
            candidates=ledger_entry.decision_log.get('candidates', []),
            decision_type=action,
            selected_candidate_id=resolution_data.get('selected_candidate_id') if resolution_data else None,
            rationale=rationale,
            decided_by=decided_by,
            decided_at=datetime.utcnow()
        )

        self.db.add(decision)

        # Update ledger entry
        if action == 'approve':
            ledger_entry.resolution_action = 'approved'
        elif action == 'reject':
            ledger_entry.resolution_action = 'rejected'
        elif action == 'fix':
            ledger_entry.resolution_action = 'fixed'
            if resolution_data:
                ledger_entry.decision_log['fixed_data'] = resolution_data
        elif action == 'match_to_candidate':
            ledger_entry.resolution_action = 'matched'
            ledger_entry.match_method = 'manual'
            if resolution_data:
                ledger_entry.decision_log['selected_candidate'] = resolution_data

        ledger_entry.quarantine_resolved_at = datetime.utcnow()
        ledger_entry.quarantine_resolved_by = decided_by

        self.db.commit()
        self.db.refresh(ledger_entry)

        return ledger_entry

    def get_quarantine_stats(
        self,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get quarantine statistics.

        Args:
            run_id: Filter by run ID

        Returns:
            Dict with counts by reason, model, status
        """
        query = self.db.query(ImportLedger).filter(
            ImportLedger.resolution_action == 'quarantined'
        )

        if run_id:
            query = query.filter(ImportLedger.run_id == run_id)

        total = query.count()
        pending = query.filter(ImportLedger.quarantine_resolved_at.is_(None)).count()
        resolved = total - pending

        # By reason
        by_reason = {}
        for entry in query.all():
            reason = entry.quarantine_reason or 'unknown'
            if reason not in by_reason:
                by_reason[reason] = {'total': 0, 'pending': 0, 'resolved': 0}
            by_reason[reason]['total'] += 1
            if entry.quarantine_resolved_at:
                by_reason[reason]['resolved'] += 1
            else:
                by_reason[reason]['pending'] += 1

        # By model
        by_model = {}
        for entry in query.all():
            model = entry.odoo_model
            if model not in by_model:
                by_model[model] = {'total': 0, 'pending': 0, 'resolved': 0}
            by_model[model]['total'] += 1
            if entry.quarantine_resolved_at:
                by_model[model]['resolved'] += 1
            else:
                by_model[model]['pending'] += 1

        return {
            'total_quarantined': total,
            'pending': pending,
            'resolved': resolved,
            'by_reason': by_reason,
            'by_model': by_model,
        }

    def _extract_source_data(self, ledger_entry: ImportLedger) -> Dict[str, Any]:
        """Extract source record data from ledger entry."""
        return {
            'src_system': ledger_entry.src_system,
            'src_table': ledger_entry.src_table,
            'src_pk': ledger_entry.src_pk,
            'natural_key_hash': ledger_entry.natural_key_hash,
            'content_hash': ledger_entry.content_hash,
        }
