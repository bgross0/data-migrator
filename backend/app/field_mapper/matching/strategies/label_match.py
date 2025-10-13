"""
Label Match Strategy.

This strategy matches columns to fields based on field label matching.
"""
from typing import List
import re

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class LabelMatchStrategy(BaseStrategy):
    """
    Matches columns to fields using field label matching.

    This strategy looks for matches between the column name and the field's
    user-facing label. It's slightly less confident than exact name matching
    but still highly reliable.

    Examples:
    - Column "Customer Name" -> Field with label "Customer Name"
    - Column "email_address" -> Field with label "Email Address"
    - Column "Qty" -> Field with label "Quantity"
    """

    def __init__(self, weight: float = 0.95):
        """
        Initialize the label match strategy.

        Args:
            weight: Strategy weight (default 0.95, slightly lower than exact match)
        """
        super().__init__(weight=weight)

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields with labels that match the column name.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with high confidence scores
        """
        column_name = context.column_profile.column_name
        logger.debug(f"LabelMatch: Searching for '{column_name}'")

        # Normalize column name
        normalized_col = self._normalize_label(column_name)

        mappings = []

        # Try exact label match first
        exact_matches = context.knowledge_base.lookup_by_label(normalized_col)

        for model_name, field_name in exact_matches:
            # Skip if we're filtering to specific models
            if context.target_models and model_name not in context.target_models:
                continue
            if context.candidate_models and model_name not in context.candidate_models:
                continue

            field = context.knowledge_base.get_field(model_name, field_name)
            if not field:
                continue

            # Calculate similarity between column and label
            similarity = self._calculate_label_similarity(
                column_name,
                field.label
            )

            confidence = similarity * 0.98  # Slightly lower than exact name match

            rationale = (
                f"Label match: column name '{column_name}' matches "
                f"field label '{field.label}' (similarity={similarity:.2f})"
            )

            scores = {
                "label_match": 1.0,
                "label_similarity": similarity,
            }

            mapping = self.create_mapping(
                field=field,
                confidence=confidence,
                rationale=rationale,
                scores=scores,
                source_column=column_name,
            )

            mappings.append(mapping)

        # Also try prefix matching using the trie
        if len(mappings) < 5:  # Only if we don't have many exact matches
            prefix_matches = context.knowledge_base.prefix_match_label(
                normalized_col,
                limit=10
            )

            for model_name, field_name in prefix_matches:
                # Skip if already in exact matches
                if (model_name, field_name) in exact_matches:
                    continue

                # Skip if we're filtering to specific models
                if context.target_models and model_name not in context.target_models:
                    continue
                if context.candidate_models and model_name not in context.candidate_models:
                    continue

                field = context.knowledge_base.get_field(model_name, field_name)
                if not field:
                    continue

                similarity = self._calculate_label_similarity(
                    column_name,
                    field.label
                )

                # Lower confidence for prefix matches
                confidence = similarity * 0.85

                rationale = (
                    f"Label prefix match: column name '{column_name}' partially matches "
                    f"field label '{field.label}' (similarity={similarity:.2f})"
                )

                scores = {
                    "label_prefix_match": 1.0,
                    "label_similarity": similarity,
                }

                mapping = self.create_mapping(
                    field=field,
                    confidence=confidence,
                    rationale=rationale,
                    scores=scores,
                    source_column=column_name,
                )

                mappings.append(mapping)

        logger.info(f"LabelMatch: Found {len(mappings)} label matches")
        return self.sort_by_confidence(mappings)

    def _normalize_label(self, label: str) -> str:
        """
        Normalize a label for comparison.

        Args:
            label: Label to normalize

        Returns:
            Normalized label (lowercase, stripped)
        """
        # Remove common prefixes/suffixes
        normalized = label.strip().lower()

        # Remove special characters but keep spaces
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)

        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def _calculate_label_similarity(self, col_name: str, field_label: str) -> float:
        """
        Calculate similarity between column name and field label.

        Args:
            col_name: Column name from spreadsheet
            field_label: Field label from Odoo

        Returns:
            Similarity score from 0.0 to 1.0
        """
        norm_col = self._normalize_label(col_name)
        norm_label = self._normalize_label(field_label)

        # Exact match after normalization
        if norm_col == norm_label:
            return 1.0

        # Check if one contains the other
        if norm_col in norm_label or norm_label in norm_col:
            shorter = min(len(norm_col), len(norm_label))
            longer = max(len(norm_col), len(norm_label))
            return shorter / longer

        # Token-based similarity (Jaccard)
        col_tokens = set(norm_col.split())
        label_tokens = set(norm_label.split())

        if not col_tokens or not label_tokens:
            return 0.0

        intersection = col_tokens & label_tokens
        union = col_tokens | label_tokens

        return len(intersection) / len(union)
