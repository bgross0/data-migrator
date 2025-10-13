"""
Statistical Similarity Strategy.

This strategy matches columns to fields based on statistical properties.
"""
from typing import List

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class StatisticalSimilarityStrategy(BaseStrategy):
    """
    Matches columns to fields based on statistical properties.

    This strategy analyzes the statistical characteristics of the column
    and matches it to fields where those characteristics make sense:
    - High uniqueness ratio -> ID fields, unique identifiers
    - Low uniqueness ratio -> status fields, categories
    - Specific value ranges -> quantity fields, percentage fields
    """

    def __init__(self, weight: float = 0.60):
        """
        Initialize the statistical similarity strategy.

        Args:
            weight: Strategy weight (default 0.60)
        """
        super().__init__(weight=weight)

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields with similar statistical properties.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with confidence scores
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        logger.debug(
            f"StatisticalSimilarity: Analyzing '{column_name}' "
            f"(uniqueness={profile.uniqueness_ratio:.2f})"
        )

        mappings = []

        # High uniqueness ratio suggests unique/ID fields
        if profile.uniqueness_ratio >= 0.95:
            mappings.extend(
                self._match_high_uniqueness(context)
            )

        # Low uniqueness ratio suggests selection/state fields
        elif profile.uniqueness_ratio <= 0.1:
            mappings.extend(
                self._match_low_uniqueness(context)
            )

        # For numeric columns, analyze value ranges
        if profile.data_type in ("integer", "float"):
            mappings.extend(
                self._match_numeric_ranges(context)
            )

        logger.info(
            f"StatisticalSimilarity: Found {len(mappings)} statistical matches"
        )

        return self.sort_by_confidence(mappings)

    def _match_high_uniqueness(
        self,
        context: MatchingContext
    ) -> List[FieldMapping]:
        """
        Match columns with high uniqueness to ID/unique fields.

        Args:
            context: MatchingContext

        Returns:
            List of FieldMapping objects
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        mappings = []

        # Look for ID fields, reference fields, unique identifiers
        id_patterns = ["id", "_id", "ref", "reference", "code", "sequence"]

        for pattern in id_patterns:
            # Use prefix matching for ID fields
            matching_keys = context.knowledge_base.prefix_match_field_name(
                pattern,
                limit=20
            )

            for model_name, field_name in matching_keys:
                # Skip if we're filtering to specific models
                if context.target_models and model_name not in context.target_models:
                    continue
                if context.candidate_models and model_name not in context.candidate_models:
                    continue

                field = context.knowledge_base.get_field(model_name, field_name)
                if not field:
                    continue

                # Check if field name contains the pattern
                if pattern.lower() not in field.name.lower():
                    continue

                confidence = 0.70 * profile.uniqueness_ratio

                rationale = (
                    f"High uniqueness ratio ({profile.uniqueness_ratio:.2f}) "
                    f"suggests unique identifier field like '{field.name}'"
                )

                scores = {
                    "uniqueness_match": 1.0,
                    "uniqueness_ratio": profile.uniqueness_ratio,
                    "is_id_pattern": 1.0,
                }

                mapping = self.create_mapping(
                    field=field,
                    confidence=confidence,
                    rationale=rationale,
                    scores=scores,
                    source_column=column_name,
                )

                mappings.append(mapping)

        return mappings

    def _match_low_uniqueness(
        self,
        context: MatchingContext
    ) -> List[FieldMapping]:
        """
        Match columns with low uniqueness to selection/state fields.

        Args:
            context: MatchingContext

        Returns:
            List of FieldMapping objects
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        mappings = []

        # Look for selection fields, state fields, status fields
        state_patterns = ["state", "status", "type", "stage", "category"]

        for pattern in state_patterns:
            matching_keys = context.knowledge_base.prefix_match_field_name(
                pattern,
                limit=20
            )

            for model_name, field_name in matching_keys:
                # Skip if we're filtering to specific models
                if context.target_models and model_name not in context.target_models:
                    continue
                if context.candidate_models and model_name not in context.candidate_models:
                    continue

                field = context.knowledge_base.get_field(model_name, field_name)
                if not field:
                    continue

                # Check if field name contains the pattern
                if pattern.lower() not in field.name.lower():
                    continue

                # Prefer selection fields
                type_bonus = 1.2 if field.field_type == "selection" else 1.0

                confidence = (0.60 * (1.0 - profile.uniqueness_ratio) * type_bonus)

                rationale = (
                    f"Low uniqueness ratio ({profile.uniqueness_ratio:.2f}) "
                    f"suggests state/selection field like '{field.name}'"
                )

                scores = {
                    "low_uniqueness_match": 1.0,
                    "uniqueness_ratio": profile.uniqueness_ratio,
                    "is_state_pattern": 1.0,
                    "is_selection_field": 1.0 if field.field_type == "selection" else 0.0,
                }

                mapping = self.create_mapping(
                    field=field,
                    confidence=confidence,
                    rationale=rationale,
                    scores=scores,
                    source_column=column_name,
                )

                mappings.append(mapping)

        return mappings

    def _match_numeric_ranges(
        self,
        context: MatchingContext
    ) -> List[FieldMapping]:
        """
        Match numeric columns based on value ranges.

        Args:
            context: MatchingContext

        Returns:
            List of FieldMapping objects
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        if profile.min_value is None or profile.max_value is None:
            return []

        mappings = []

        # Percentage fields (values between 0 and 100)
        if 0 <= profile.min_value <= 100 and 0 <= profile.max_value <= 100:
            percentage_patterns = ["percent", "percentage", "rate", "ratio"]

            for pattern in percentage_patterns:
                matching_keys = context.knowledge_base.prefix_match_field_name(
                    pattern,
                    limit=10
                )

                for model_name, field_name in matching_keys:
                    if context.target_models and model_name not in context.target_models:
                        continue
                    if context.candidate_models and model_name not in context.candidate_models:
                        continue

                    field = context.knowledge_base.get_field(model_name, field_name)
                    if not field or field.field_type not in ("float", "integer"):
                        continue

                    confidence = 0.55

                    rationale = (
                        f"Value range [{profile.min_value}, {profile.max_value}] "
                        f"suggests percentage field like '{field.name}'"
                    )

                    scores = {
                        "range_match": 1.0,
                        "min_value": profile.min_value,
                        "max_value": profile.max_value,
                        "is_percentage_range": 1.0,
                    }

                    mapping = self.create_mapping(
                        field=field,
                        confidence=confidence,
                        rationale=rationale,
                        scores=scores,
                        source_column=column_name,
                    )

                    mappings.append(mapping)

        return mappings
