"""
Contextual Match Strategy.

This strategy matches columns to fields based on context from other columns.
"""
from typing import List, Set

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class ContextualMatchStrategy(BaseStrategy):
    """
    Matches columns to fields based on contextual information.

    This strategy analyzes the other columns in the same sheet to provide
    context about what model is likely being imported. For example:
    - If there are columns for "customer_id", "email", "phone" -> res.partner
    - If there are columns for "product_code", "price", "qty" -> product.product
    - If there are columns for "order_date", "total", "partner" -> sale.order

    Once the likely model is identified, it boosts the confidence of fields
    from that model.
    """

    def __init__(self, weight: float = 0.80):
        """
        Initialize the contextual match strategy.

        Args:
            weight: Strategy weight (default 0.80)
        """
        super().__init__(weight=weight)

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields considering the context of other columns.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with confidence scores
        """
        column_name = context.column_profile.column_name
        logger.debug(f"ContextualMatch: Analyzing '{column_name}' with context")

        # Detect likely models from all columns in the sheet
        likely_models = self._detect_likely_models(context)

        if not likely_models:
            logger.debug("ContextualMatch: No likely models detected from context")
            return []

        logger.info(
            f"ContextualMatch: Detected likely models: "
            f"{', '.join(list(likely_models)[:5])}"
        )

        mappings = []

        # Look for fields in the likely models
        for model_name in likely_models:
            if context.target_models and model_name not in context.target_models:
                continue
            if context.candidate_models and model_name not in context.candidate_models:
                continue

            model = context.knowledge_base.get_model(model_name)
            if not model:
                continue

            # Get all fields for this model
            model_fields = context.knowledge_base.get_model_fields(model_name)

            for field in model_fields:
                # Calculate similarity between column name and field
                similarity = self._calculate_name_similarity(column_name, field.name)

                if similarity < 0.3:  # Only consider reasonable matches
                    continue

                confidence = similarity * 0.85  # Good confidence for contextual matches

                rationale = (
                    f"Contextual match: model '{model_name}' detected from sheet context, "
                    f"field '{field.name}' is a reasonable match (similarity={similarity:.2f})"
                )

                scores = {
                    "contextual_model_match": 1.0,
                    "name_similarity": similarity,
                    "model_detected": model_name,
                }

                mapping = self.create_mapping(
                    field=field,
                    confidence=confidence,
                    rationale=rationale,
                    scores=scores,
                    source_column=column_name,
                )

                mappings.append(mapping)

        logger.info(f"ContextualMatch: Found {len(mappings)} contextual matches")
        return self.sort_by_confidence(mappings)

    def _detect_likely_models(self, context: MatchingContext) -> Set[str]:
        """
        Detect likely models based on all columns in the sheet.

        Args:
            context: MatchingContext with all column profiles

        Returns:
            Set of likely model names
        """
        from collections import Counter

        model_votes = Counter()

        # Analyze each column to vote for models
        for col_profile in context.all_column_profiles:
            col_name = col_profile.column_name.lower().strip()

            # Look for exact field name matches
            matches = context.knowledge_base.lookup_by_field_name(col_name)
            for model_name, _ in matches:
                model_votes[model_name] += 2  # Higher weight for exact matches

            # Look for label matches
            label_matches = context.knowledge_base.lookup_by_label(col_name)
            for model_name, _ in label_matches:
                model_votes[model_name] += 1

        # Return models with at least 3 votes
        threshold = max(3, len(context.all_column_profiles) * 0.2)
        likely_models = {
            model for model, votes in model_votes.items()
            if votes >= threshold
        }

        # Also include related models (1 hop away)
        expanded_models = set(likely_models)
        for model_name in likely_models:
            related = context.knowledge_base.get_related_models(model_name, max_depth=1)
            expanded_models.update(related)

        return expanded_models

    def _calculate_name_similarity(self, col_name: str, field_name: str) -> float:
        """
        Calculate similarity between column name and field name.

        Args:
            col_name: Column name from spreadsheet
            field_name: Field name from Odoo

        Returns:
            Similarity score from 0.0 to 1.0
        """
        import re

        # Normalize both names
        norm_col = re.sub(r"[^a-z0-9]", "", col_name.lower())
        norm_field = re.sub(r"[^a-z0-9]", "", field_name.lower())

        # Exact match
        if norm_col == norm_field:
            return 1.0

        # One contains the other
        if norm_col in norm_field:
            return len(norm_col) / len(norm_field)
        if norm_field in norm_col:
            return len(norm_field) / len(norm_col)

        # Token-based similarity
        col_tokens = set(re.findall(r"[a-z0-9]+", col_name.lower()))
        field_tokens = set(re.findall(r"[a-z0-9]+", field_name.lower()))

        if not col_tokens or not field_tokens:
            return 0.0

        intersection = col_tokens & field_tokens
        union = col_tokens | field_tokens

        return len(intersection) / len(union) if union else 0.0
