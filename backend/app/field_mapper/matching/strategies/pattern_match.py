"""
Pattern Match Strategy.

This strategy matches columns to fields based on detected patterns in the data.
"""
from typing import List, Dict

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class PatternMatchStrategy(BaseStrategy):
    """
    Matches columns to fields based on data patterns.

    This strategy uses pattern detection from the column profile to identify
    specific field types:
    - Email pattern -> email field
    - Phone pattern -> phone field
    - URL pattern -> website/url field
    - Currency pattern -> monetary field
    - Date pattern -> date field
    """

    # Mapping of patterns to likely field names
    PATTERN_TO_FIELDS: Dict[str, List[str]] = {
        "email": ["email", "email_from", "partner_email", "user_email"],
        "phone": ["phone", "mobile", "telephone", "partner_phone"],
        "url": ["website", "url", "website_url", "link"],
        "currency": ["amount", "price", "cost", "total", "subtotal", "value"],
        "date": ["date", "create_date", "write_date", "date_order", "date_deadline"],
    }

    # Mapping of patterns to Odoo field types
    PATTERN_TO_TYPES: Dict[str, List[str]] = {
        "email": ["char"],
        "phone": ["char"],
        "url": ["char"],
        "currency": ["monetary", "float"],
        "date": ["date", "datetime"],
    }

    def __init__(self, weight: float = 0.75):
        """
        Initialize the pattern match strategy.

        Args:
            weight: Strategy weight (default 0.75)
        """
        super().__init__(weight=weight)
        self.min_pattern_ratio = 0.7  # At least 70% of values should match pattern

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields that match detected patterns in the column.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with confidence scores
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        logger.debug(f"PatternMatch: Analyzing '{column_name}'")

        if not profile.patterns:
            logger.debug("PatternMatch: No patterns detected in column")
            return []

        mappings = []

        # Process each detected pattern
        for pattern_name, pattern_ratio in profile.patterns.items():
            if pattern_ratio < self.min_pattern_ratio:
                logger.debug(
                    f"PatternMatch: Skipping pattern '{pattern_name}' "
                    f"(ratio={pattern_ratio:.2f} < {self.min_pattern_ratio})"
                )
                continue

            logger.debug(
                f"PatternMatch: Processing pattern '{pattern_name}' "
                f"(ratio={pattern_ratio:.2f})"
            )

            # Get likely field names for this pattern
            likely_field_names = self.PATTERN_TO_FIELDS.get(pattern_name, [])

            # Get likely field types for this pattern
            likely_field_types = self.PATTERN_TO_TYPES.get(pattern_name, [])

            # Search by field names
            for field_name in likely_field_names:
                matching_keys = context.knowledge_base.lookup_by_field_name(field_name)

                for model_name, matched_field_name in matching_keys:
                    # Skip if we're filtering to specific models
                    if context.target_models and model_name not in context.target_models:
                        continue
                    if context.candidate_models and model_name not in context.candidate_models:
                        continue

                    field = context.knowledge_base.get_field(model_name, matched_field_name)
                    if not field:
                        continue

                    # Bonus if field type also matches
                    type_bonus = 1.2 if field.field_type in likely_field_types else 1.0

                    confidence = (pattern_ratio * 0.8 * type_bonus)

                    rationale = (
                        f"Pattern match: column contains '{pattern_name}' pattern "
                        f"(ratio={pattern_ratio:.2f}), matching field name '{field_name}'"
                    )

                    scores = {
                        "pattern_detected": pattern_name,
                        "pattern_ratio": pattern_ratio,
                        "field_name_match": 1.0,
                        "field_type_match": 1.0 if type_bonus > 1.0 else 0.0,
                    }

                    mapping = self.create_mapping(
                        field=field,
                        confidence=confidence,
                        rationale=rationale,
                        scores=scores,
                        source_column=column_name,
                    )

                    mappings.append(mapping)

            # Also search by field types
            for field_type in likely_field_types:
                matching_keys = context.knowledge_base.lookup_by_type(field_type)

                for model_name, matched_field_name in matching_keys:
                    # Skip if we're filtering to specific models
                    if context.target_models and model_name not in context.target_models:
                        continue
                    if context.candidate_models and model_name not in context.candidate_models:
                        continue

                    field = context.knowledge_base.get_field(model_name, matched_field_name)
                    if not field:
                        continue

                    # Lower confidence for type-only matches
                    confidence = pattern_ratio * 0.6

                    rationale = (
                        f"Pattern match: column contains '{pattern_name}' pattern "
                        f"(ratio={pattern_ratio:.2f}), compatible with field type '{field_type}'"
                    )

                    scores = {
                        "pattern_detected": pattern_name,
                        "pattern_ratio": pattern_ratio,
                        "field_type_match": 1.0,
                    }

                    mapping = self.create_mapping(
                        field=field,
                        confidence=confidence,
                        rationale=rationale,
                        scores=scores,
                        source_column=column_name,
                    )

                    mappings.append(mapping)

        # Remove duplicates (keep highest confidence for each field)
        unique_mappings = {}
        for mapping in mappings:
            key = (mapping.target_model, mapping.target_field)
            if key not in unique_mappings or mapping.confidence > unique_mappings[key].confidence:
                unique_mappings[key] = mapping

        result = list(unique_mappings.values())

        logger.info(f"PatternMatch: Found {len(result)} pattern-based matches")
        return self.sort_by_confidence(result)
