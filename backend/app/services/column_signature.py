"""
Column Signature Detector.

Detects entity types and relationships from column name patterns and values.
Uses domain knowledge and pattern matching to infer semantic meaning.

Examples:
    ['customer_name', 'customer_email', 'customer_phone'] → res.partner (company)
    ['contact_name', 'contact_email', 'company'] → res.partner (contact)
    ['lead_name', 'stage', 'expected_revenue'] → crm.lead
    ['activity_1', 'activity_2', 'activity_3'] → pivot candidate (mail.activity)
"""
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import re
from collections import Counter


@dataclass
class EntitySignature:
    """
    Detected entity type signature.

    Attributes:
        entity_type: Detected entity ('res.partner', 'crm.lead', etc.)
        confidence: Confidence score (0.0-1.0)
        matched_columns: Columns that matched signature patterns
        evidence: Evidence supporting this inference
    """
    entity_type: str
    confidence: float
    matched_columns: List[str]
    evidence: Dict[str, any]


@dataclass
class RelationshipSignature:
    """
    Detected relationship between columns.

    Attributes:
        source_entity: Source entity type
        target_entity: Target entity type
        relationship_type: Type ('many2one', 'one2many', 'many2many')
        source_column: Source column name
        target_column: Target column name (if applicable)
        confidence: Confidence score
    """
    source_entity: str
    target_entity: str
    relationship_type: str
    source_column: str
    target_column: Optional[str]
    confidence: float


class ColumnSignatureDetector:
    """
    Detects entity types and relationships from column signatures.

    Uses pattern matching on column names and value analysis to infer
    the semantic meaning of columns and their relationships.
    """

    # Entity signature patterns
    # Format: entity_type → (required_patterns, optional_patterns, weight)
    ENTITY_PATTERNS = {
        'res.partner.company': {
            'required': [
                r'(customer|client|company|organization|partner).*name',
                r'(customer|client|company|partner).*email',
            ],
            'optional': [
                r'(customer|client|company).*phone',
                r'(customer|client|company).*address',
                r'(customer|client|company).*city',
                r'vat|tax.*id|ein',
                r'street',
                r'zip|postal.*code',
            ],
            'weight': 1.0,
        },
        'res.partner.contact': {
            'required': [
                r'contact.*name',
                r'contact.*email',
            ],
            'optional': [
                r'contact.*phone',
                r'contact.*title',
                r'company.*name',
                r'parent.*company',
            ],
            'weight': 1.0,
        },
        'crm.lead': {
            'required': [
                r'lead.*name|opportunity.*name',
                r'stage|pipeline.*stage',
            ],
            'optional': [
                r'expected.*revenue|deal.*value|amount',
                r'probability',
                r'source|utm.*source',
                r'campaign|utm.*campaign',
                r'lost.*reason',
                r'owner|salesperson|assigned.*to',
            ],
            'weight': 1.0,
        },
        'mail.activity': {
            'required': [
                r'activity.*type|task.*type',
                r'due.*date|deadline',
            ],
            'optional': [
                r'assigned.*to|owner',
                r'summary|subject',
                r'note|description',
                r'status|state',
            ],
            'weight': 0.9,
        },
        'mail.message': {
            'required': [
                r'message|note|comment',
                r'date|timestamp|created.*at',
            ],
            'optional': [
                r'author',
                r'subject',
                r'body',
                r'type',
            ],
            'weight': 0.9,
        },
        'sale.order': {
            'required': [
                r'order.*number|po.*number',
                r'order.*date',
            ],
            'optional': [
                r'customer|partner',
                r'total|amount',
                r'status|state',
                r'salesperson',
            ],
            'weight': 1.0,
        },
        'product.product': {
            'required': [
                r'product.*name|item.*name',
                r'sku|product.*code|item.*code',
            ],
            'optional': [
                r'price|unit.*price',
                r'cost',
                r'category',
                r'type',
            ],
            'weight': 1.0,
        },
    }

    # Relationship indicators
    RELATIONSHIP_PATTERNS = {
        'many2one': [
            r'.*_id$',
            r'.*_name$',
            r'customer|partner|company',
            r'owner|salesperson|user',
            r'stage|status',
        ],
        'one2many': [
            r'(activity|note|task|message)_\d+$',  # activity_1, activity_2, etc.
            r'(line|item)_\d+$',  # order_line_1, order_line_2, etc.
        ],
        'many2many': [
            r'tags?|categories',
            r'skills?',
        ],
    }

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize detector.

        Args:
            confidence_threshold: Minimum confidence for auto-inference
        """
        self.confidence_threshold = confidence_threshold

    def detect_entity_type(
        self,
        column_names: List[str],
        sample_data: Optional[List[Dict[str, any]]] = None
    ) -> List[EntitySignature]:
        """
        Detect entity types from column names.

        Args:
            column_names: List of column names
            sample_data: Optional sample rows for value analysis

        Returns:
            List of detected entity signatures, sorted by confidence
        """
        signatures = []

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            required_matches = self._match_patterns(column_names, patterns['required'])
            optional_matches = self._match_patterns(column_names, patterns['optional'])

            # Calculate confidence
            if len(required_matches) >= len(patterns['required']):
                # All required patterns matched
                confidence = patterns['weight']

                # Boost confidence for optional matches
                if patterns['optional']:
                    optional_ratio = len(optional_matches) / len(patterns['optional'])
                    confidence = min(1.0, confidence + 0.2 * optional_ratio)

                all_matches = list(set(required_matches + optional_matches))

                signature = EntitySignature(
                    entity_type=entity_type,
                    confidence=confidence,
                    matched_columns=all_matches,
                    evidence={
                        'required_matches': len(required_matches),
                        'required_total': len(patterns['required']),
                        'optional_matches': len(optional_matches),
                        'optional_total': len(patterns['optional']),
                    }
                )

                signatures.append(signature)

        # Sort by confidence descending
        signatures.sort(key=lambda s: s.confidence, reverse=True)

        return signatures

    def _match_patterns(
        self,
        column_names: List[str],
        patterns: List[str]
    ) -> List[str]:
        """
        Match column names against regex patterns.

        Returns:
            List of columns that matched any pattern
        """
        matches = []
        for col in column_names:
            normalized = col.lower().strip().replace(' ', '_')
            for pattern in patterns:
                if re.search(pattern, normalized):
                    matches.append(col)
                    break  # Only count each column once
        return matches

    def detect_relationships(
        self,
        column_names: List[str],
        entity_type: Optional[str] = None
    ) -> List[RelationshipSignature]:
        """
        Detect relationships from column names.

        Args:
            column_names: List of column names
            entity_type: Known entity type (if available)

        Returns:
            List of detected relationships
        """
        relationships = []

        # Detect many2one relationships
        for col in column_names:
            normalized = col.lower().strip()
            for pattern in self.RELATIONSHIP_PATTERNS['many2one']:
                if re.search(pattern, normalized):
                    # Infer target entity
                    target = self._infer_target_entity(col, normalized)
                    if target:
                        relationships.append(RelationshipSignature(
                            source_entity=entity_type or 'unknown',
                            target_entity=target,
                            relationship_type='many2one',
                            source_column=col,
                            target_column=None,
                            confidence=0.8
                        ))
                    break

        # Detect one2many (pivot candidates)
        pivot_groups = self._detect_pivot_groups(column_names)
        for prefix, cols in pivot_groups.items():
            target = self._infer_target_from_prefix(prefix)
            relationships.append(RelationshipSignature(
                source_entity=entity_type or 'unknown',
                target_entity=target,
                relationship_type='one2many',
                source_column=', '.join(cols),
                target_column=None,
                confidence=0.9
            ))

        # Detect many2many
        for col in column_names:
            normalized = col.lower().strip()
            for pattern in self.RELATIONSHIP_PATTERNS['many2many']:
                if re.search(pattern, normalized):
                    relationships.append(RelationshipSignature(
                        source_entity=entity_type or 'unknown',
                        target_entity='tags',
                        relationship_type='many2many',
                        source_column=col,
                        target_column=None,
                        confidence=0.7
                    ))
                    break

        return relationships

    def _infer_target_entity(self, col: str, normalized: str) -> Optional[str]:
        """Infer target entity from column name."""
        if 'customer' in normalized or 'partner' in normalized or 'company' in normalized:
            return 'res.partner'
        if 'user' in normalized or 'owner' in normalized or 'salesperson' in normalized:
            return 'res.users'
        if 'stage' in normalized:
            return 'crm.stage'
        if 'product' in normalized or 'item' in normalized:
            return 'product.product'
        if 'lost.*reason' in normalized:
            return 'crm.lost.reason'
        return None

    def _detect_pivot_groups(self, column_names: List[str]) -> Dict[str, List[str]]:
        """
        Detect numbered column groups (pivot candidates).

        Example:
            ['activity_1', 'activity_2', 'activity_3'] → {'activity': [...]  }
            ['note_date_1', 'note_text_1', 'note_date_2', 'note_text_2'] → {'note': [...]}
        """
        # Pattern: prefix_number or prefix_field_number
        pivot_pattern = r'^([a-z_]+?)_?\d+$'
        groups = {}

        for col in column_names:
            normalized = col.lower().strip()
            match = re.match(pivot_pattern, normalized)
            if match:
                prefix = match.group(1)
                if prefix not in groups:
                    groups[prefix] = []
                groups[prefix].append(col)

        # Filter: only groups with 2+ columns
        return {k: v for k, v in groups.items() if len(v) >= 2}

    def _infer_target_from_prefix(self, prefix: str) -> str:
        """Infer target entity from pivot column prefix."""
        if 'activity' in prefix or 'task' in prefix:
            return 'mail.activity'
        if 'note' in prefix or 'message' in prefix or 'comment' in prefix:
            return 'mail.message'
        if 'line' in prefix or 'item' in prefix:
            return 'sale.order.line'
        return 'unknown'

    def generate_summary(
        self,
        entity_signatures: List[EntitySignature],
        relationships: List[RelationshipSignature]
    ) -> Dict[str, any]:
        """
        Generate human-readable summary of detections.

        Returns:
            Dict with summary info
        """
        return {
            "detected_entities": [
                {
                    "type": sig.entity_type,
                    "confidence": f"{sig.confidence:.0%}",
                    "matched_columns": len(sig.matched_columns),
                }
                for sig in entity_signatures
            ],
            "detected_relationships": [
                {
                    "type": rel.relationship_type,
                    "target": rel.target_entity,
                    "confidence": f"{rel.confidence:.0%}",
                }
                for rel in relationships
            ],
            "primary_entity": entity_signatures[0].entity_type if entity_signatures else "unknown",
            "requires_confirmation": any(
                sig.confidence < self.confidence_threshold for sig in entity_signatures
            ),
        }
