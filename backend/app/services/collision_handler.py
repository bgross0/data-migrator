"""
Collision Handler Service.

Handles multi-match scenarios from identity resolution where a source record
matches multiple existing canonical/Odoo records with similar confidence scores.

Implements HITL (Human-in-the-Loop) workflow:
1. Detect collision (2+ candidates with similar scores)
2. Quarantine source record
3. Present candidates to user for review
4. Apply user decision
5. Log decision for audit
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.ledger import ImportLedger, ImportDecision
from app.services.identity_resolution import MatchCandidate, MatchResult


@dataclass
class CollisionResolution:
    """
    User's resolution of a collision.

    Attributes:
        action: Decision type ('match_to_candidate', 'create_new', 'skip', 'merge')
        selected_candidate_sk: Canonical surrogate key if action='match_to_candidate'
        rationale: User's explanation
        decided_by: User email/ID
    """
    action: str
    selected_candidate_sk: Optional[int]
    rationale: Optional[str]
    decided_by: str


class CollisionHandler:
    """
    Handles multi-match collisions in identity resolution.

    When identity resolution produces multiple candidates with similar scores,
    this service quarantines the record and manages HITL workflow.
    """

    def __init__(self, db: Session):
        """
        Initialize collision handler.

        Args:
            db: Database session
        """
        self.db = db

    def handle_collision(
        self,
        match_result: MatchResult,
        source_record: Dict[str, Any],
        odoo_model: str,
        run_id: int,
        batch_id: str
    ) -> ImportLedger:
        """
        Handle collision by quarantining record.

        Args:
            match_result: MatchResult with action='multi_match'
            source_record: Source data from staging
            odoo_model: Target Odoo model
            run_id: Current run ID
            batch_id: Current batch ID

        Returns:
            Created ImportLedger entry with resolution_action='quarantined'
        """
        if match_result.action != 'multi_match':
            raise ValueError(f"Expected multi_match, got {match_result.action}")

        # Create ledger entry with quarantine status
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
            odoo_id=None,  # Not yet resolved
            external_id=None,
            resolution_action='quarantined',
            match_confidence=match_result.confidence,
            match_method='multi_match',
            decision_log={
                'candidates': [self._candidate_to_dict(c) for c in match_result.candidates],
                'quarantine_reason': match_result.quarantine_reason,
                'quarantined_at': datetime.utcnow().isoformat(),
            },
            quarantine_reason=match_result.quarantine_reason,
            quarantine_resolved_at=None,
            quarantine_resolved_by=None,
        )

        self.db.add(ledger_entry)
        self.db.commit()
        self.db.refresh(ledger_entry)

        return ledger_entry

    def resolve_collision(
        self,
        ledger_id: int,
        resolution: CollisionResolution
    ) -> ImportLedger:
        """
        Resolve collision with user decision.

        Args:
            ledger_id: ImportLedger ID
            resolution: User's decision

        Returns:
            Updated ImportLedger entry

        Raises:
            ValueError: If ledger entry not found or not quarantined
        """
        ledger_entry = self.db.query(ImportLedger).filter(
            ImportLedger.id == ledger_id
        ).first()

        if not ledger_entry:
            raise ValueError(f"Ledger entry {ledger_id} not found")

        if ledger_entry.resolution_action != 'quarantined':
            raise ValueError(f"Ledger entry {ledger_id} is not quarantined (status: {ledger_entry.resolution_action})")

        # Create decision record
        decision_log = ImportDecision(
            ledger_id=ledger_id,
            source_data=self._extract_source_data(ledger_entry),
            candidates=ledger_entry.decision_log.get('candidates', []),
            decision_type=resolution.action,
            selected_candidate_id=resolution.selected_candidate_sk,
            rationale=resolution.rationale,
            decided_by=resolution.decided_by,
            decided_at=datetime.utcnow()
        )

        self.db.add(decision_log)

        # Update ledger entry
        if resolution.action == 'match_to_candidate':
            # User chose to match to a specific candidate
            ledger_entry.resolution_action = 'matched'
            # Note: selected_candidate_sk is canonical SK, need to get odoo_id
            # This would require looking up the canonical record
            # For now, store the SK in decision_log
            ledger_entry.decision_log['selected_candidate_sk'] = resolution.selected_candidate_sk
            ledger_entry.match_method = 'manual'

        elif resolution.action == 'create_new':
            # User chose to create new record
            ledger_entry.resolution_action = 'created'
            ledger_entry.match_method = 'manual'

        elif resolution.action == 'skip':
            # User chose to skip this record
            ledger_entry.resolution_action = 'skipped'

        elif resolution.action == 'merge':
            # User chose to merge candidates (advanced)
            ledger_entry.resolution_action = 'merged'
            ledger_entry.decision_log['merge_target'] = resolution.selected_candidate_sk

        # Mark as resolved
        ledger_entry.quarantine_resolved_at = datetime.utcnow()
        ledger_entry.quarantine_resolved_by = resolution.decided_by

        self.db.commit()
        self.db.refresh(ledger_entry)

        return ledger_entry

    def get_quarantine_queue(
        self,
        run_id: Optional[int] = None,
        odoo_model: Optional[str] = None,
        limit: int = 50
    ) -> List[ImportLedger]:
        """
        Get quarantined records for HITL review.

        Args:
            run_id: Filter by run ID (optional)
            odoo_model: Filter by Odoo model (optional)
            limit: Maximum number of records to return

        Returns:
            List of quarantined ImportLedger entries
        """
        query = self.db.query(ImportLedger).filter(
            ImportLedger.resolution_action == 'quarantined',
            ImportLedger.quarantine_resolved_at.is_(None)
        )

        if run_id:
            query = query.filter(ImportLedger.run_id == run_id)

        if odoo_model:
            query = query.filter(ImportLedger.odoo_model == odoo_model)

        query = query.order_by(ImportLedger.created_at.desc())
        query = query.limit(limit)

        return query.all()

    def get_collision_details(self, ledger_id: int) -> Dict[str, Any]:
        """
        Get detailed collision information for HITL UI.

        Args:
            ledger_id: ImportLedger ID

        Returns:
            Dict with collision details for display
        """
        ledger_entry = self.db.query(ImportLedger).filter(
            ImportLedger.id == ledger_id
        ).first()

        if not ledger_entry:
            raise ValueError(f"Ledger entry {ledger_id} not found")

        candidates = ledger_entry.decision_log.get('candidates', [])

        return {
            'ledger_id': ledger_id,
            'source_record': self._extract_source_data(ledger_entry),
            'odoo_model': ledger_entry.odoo_model,
            'quarantine_reason': ledger_entry.quarantine_reason,
            'confidence': ledger_entry.match_confidence,
            'candidates': candidates,
            'candidate_count': len(candidates),
            'quarantined_at': ledger_entry.created_at.isoformat(),
        }

    def _candidate_to_dict(self, candidate: MatchCandidate) -> Dict[str, Any]:
        """Convert MatchCandidate to dict for storage."""
        return {
            'record_id': candidate.record_id,
            'score': candidate.score,
            'match_logic': candidate.match_logic,
            'record_data': candidate.record_data,
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

    def get_collision_stats(self, run_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get collision statistics.

        Args:
            run_id: Filter by run ID (optional)

        Returns:
            Dict with collision counts and averages
        """
        query = self.db.query(ImportLedger).filter(
            ImportLedger.resolution_action == 'quarantined'
        )

        if run_id:
            query = query.filter(ImportLedger.run_id == run_id)

        total_quarantined = query.count()

        resolved_query = query.filter(ImportLedger.quarantine_resolved_at.isnot(None))
        resolved_count = resolved_query.count()

        pending_count = total_quarantined - resolved_count

        # Breakdown by model
        model_counts = {}
        for entry in query.all():
            model = entry.odoo_model
            if model not in model_counts:
                model_counts[model] = {'total': 0, 'resolved': 0, 'pending': 0}
            model_counts[model]['total'] += 1
            if entry.quarantine_resolved_at:
                model_counts[model]['resolved'] += 1
            else:
                model_counts[model]['pending'] += 1

        return {
            'total_quarantined': total_quarantined,
            'resolved': resolved_count,
            'pending': pending_count,
            'by_model': model_counts,
        }
