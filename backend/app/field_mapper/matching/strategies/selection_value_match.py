"""
Selection Value Match Strategy.

This strategy matches columns to selection fields based on the values in the column.
"""
from typing import List, Set

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class SelectionValueMatchStrategy(BaseStrategy):
    """
    Matches columns to selection fields by analyzing column values.

    If a column contains values that match a field's selection options,
    it's likely to be that selection field.

    Examples:
    - Column with values ["draft", "confirmed", "done"] -> Field with same selection values
    - Column with values ["male", "female"] -> Gender field
    """

    def __init__(self, weight: float = 0.90):
        """
        Initialize the selection value match strategy.

        Args:
            weight: Strategy weight (default 0.90)
        """
        super().__init__(weight=weight)
        self.min_match_ratio = 0.5  # At least 50% of values should match

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find selection fields whose values match the column's values.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with confidence scores
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        logger.debug(f"SelectionValueMatch: Analyzing '{column_name}'")

        # Get unique values from the column (normalized)
        if not profile.value_frequencies:
            logger.debug("SelectionValueMatch: No value frequencies in profile")
            return []

        # Get unique values from the column
        column_values = set(
            str(v).lower().strip()
            for v in profile.value_frequencies.keys()
            if v is not None and str(v).strip() != ""
        )

        if not column_values:
            logger.debug("SelectionValueMatch: No valid values in column")
            return []

        logger.debug(f"SelectionValueMatch: Column has {len(column_values)} unique values")

        mappings = []
        checked_fields = set()

        # For each unique value, find fields that have it as a selection option
        for value in column_values:
            matching_keys = context.knowledge_base.lookup_by_selection_value(value)

            for model_name, field_name in matching_keys:
                # Skip if already checked
                if (model_name, field_name) in checked_fields:
                    continue
                checked_fields.add((model_name, field_name))

                # Skip if we're filtering to specific models
                if context.target_models and model_name not in context.target_models:
                    continue
                if context.candidate_models and model_name not in context.candidate_models:
                    continue

                field = context.knowledge_base.get_field(model_name, field_name)
                if not field:
                    continue

                # Get all selection values for this field
                field_selection_values = set(
                    v.lower().strip()
                    for v in field.selection_values
                )

                if not field_selection_values:
                    continue

                # Calculate match ratio
                matches = column_values & field_selection_values
                match_ratio = len(matches) / len(column_values)

                # Also calculate coverage (how many of the field's selections are used)
                coverage = len(matches) / len(field_selection_values)

                # Only create mapping if match ratio is above threshold
                if match_ratio >= self.min_match_ratio:
                    # Confidence is based on match ratio and coverage
                    confidence = (match_ratio * 0.7 + coverage * 0.3)

                    rationale = (
                        f"Selection values match: {len(matches)}/{len(column_values)} "
                        f"column values match field selections "
                        f"(match_ratio={match_ratio:.2f}, coverage={coverage:.2f})"
                    )

                    scores = {
                        "selection_match": match_ratio,
                        "selection_coverage": coverage,
                        "matched_values": len(matches),
                        "total_column_values": len(column_values),
                        "total_field_values": len(field_selection_values),
                    }

                    mapping = self.create_mapping(
                        field=field,
                        confidence=confidence,
                        rationale=rationale,
                        scores=scores,
                        source_column=column_name,
                    )

                    mappings.append(mapping)
                    logger.debug(
                        f"SelectionValueMatch: Found {model_name}.{field_name} "
                        f"(match_ratio={match_ratio:.2f})"
                    )

        logger.info(f"SelectionValueMatch: Found {len(mappings)} selection matches")
        return self.sort_by_confidence(mappings)
