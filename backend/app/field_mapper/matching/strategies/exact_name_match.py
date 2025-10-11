"""
Exact Name Match Strategy.

This strategy matches columns to fields based on exact field name matches.
"""
from typing import List

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ..compound_name_parser import CompoundNameParser
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class ExactNameMatchStrategy(BaseStrategy):
    """
    Matches columns to fields using exact field name matching.

    This is the highest confidence matching strategy. If the column name
    exactly matches a field's technical name (case-insensitive), it's very
    likely to be the correct match.

    Also handles compound names like "customer_name" -> res.partner.name

    Examples:
    - Column "customer_id" -> Field "customer_id"
    - Column "email" -> Field "email"
    - Column "Name" -> Field "name"
    - Column "customer_name" -> res.partner.name
    - Column "product_price" -> product.product.list_price
    """

    def __init__(self, weight: float = 1.0):
        """Initialize with compound name parser."""
        super().__init__(weight=weight)
        self.parser = CompoundNameParser()

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields with names that exactly match the column name.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with high confidence scores
        """
        column_name = context.column_profile.column_name
        logger.debug(f"ExactNameMatch: Searching for '{column_name}'")

        # Parse compound names
        hints = self.parser.extract_all_hints(column_name)

        mappings = []

        # First try exact match with full column name
        normalized_col = column_name.lower().strip()
        matching_keys = context.knowledge_base.lookup_by_field_name(normalized_col)

        for model_name, field_name in matching_keys:
            # Skip if we're filtering to specific models
            if context.target_models and model_name not in context.target_models:
                continue
            if context.candidate_models and model_name not in context.candidate_models:
                continue

            field = context.knowledge_base.get_field(model_name, field_name)
            if not field:
                continue

            # Calculate confidence based on exact match
            confidence = 1.0  # Perfect match

            rationale = (
                f"Exact match: column name '{column_name}' matches "
                f"field name '{field.name}'"
            )

            scores = {
                "exact_match": 1.0,
                "name_similarity": 1.0,
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
                f"ExactNameMatch: Found {model_name}.{field_name} "
                f"(confidence={confidence})"
            )

        # If compound name, also try matching the field part with model hint
        if hints["is_compound"] and hints["suggested_model"]:
            field_name_to_match = hints["field_name"]
            suggested_model = hints["suggested_model"]

            # Look for the field name in the suggested model
            matching_keys_compound = context.knowledge_base.lookup_by_field_name(field_name_to_match)

            for model_name, field_name in matching_keys_compound:
                # Prefer the suggested model
                if model_name != suggested_model:
                    continue

                # Skip if we're filtering to specific models
                if context.target_models and model_name not in context.target_models:
                    continue

                field = context.knowledge_base.get_field(model_name, field_name)
                if not field:
                    continue

                # High confidence for compound name match with correct model
                confidence = 0.95

                rationale = (
                    f"Compound name match: '{hints['entity_prefix']}' suggests {suggested_model}, "
                    f"field '{field_name_to_match}' matches '{field.name}'"
                )

                scores = {
                    "compound_match": 1.0,
                    "name_similarity": 0.95,
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
                    f"ExactNameMatch: Found compound match {model_name}.{field_name} "
                    f"(confidence={confidence})"
                )

        logger.info(f"ExactNameMatch: Found {len(mappings)} matches")
        return self.sort_by_confidence(mappings)
