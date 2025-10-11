"""
Data Type Compatibility Strategy.

This strategy matches columns to fields based on data type compatibility.
"""
from typing import List, Dict, Set

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class DataTypeCompatibilityStrategy(BaseStrategy):
    """
    Matches columns to fields based on data type compatibility.

    This strategy checks if the column's detected data type is compatible
    with the field's type in Odoo.

    Type compatibility matrix:
    - integer -> integer, float, char, many2one
    - float -> float, monetary, char
    - boolean -> boolean, selection, char
    - date -> date, datetime, char
    - string -> char, text, selection, many2one, many2many, html
    """

    # Mapping of column data types to compatible Odoo field types
    TYPE_COMPATIBILITY: Dict[str, Set[str]] = {
        "integer": {"integer", "float", "monetary", "char", "text", "many2one"},
        "float": {"float", "monetary", "char", "text"},
        "boolean": {"boolean", "selection", "char", "text"},
        "date": {"date", "datetime", "char", "text"},
        "string": {
            "char", "text", "selection", "many2one", "one2many",
            "many2many", "html", "binary", "reference"
        },
        "null": set(),  # No compatibility for null columns
    }

    def __init__(self, weight: float = 0.70):
        """
        Initialize the data type compatibility strategy.

        Args:
            weight: Strategy weight (default 0.70)
        """
        super().__init__(weight=weight)

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields with compatible data types.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with confidence scores
        """
        column_name = context.column_profile.column_name
        profile = context.column_profile

        logger.debug(
            f"DataTypeCompatibility: Analyzing '{column_name}' "
            f"(type={profile.data_type})"
        )

        # Get compatible Odoo field types
        compatible_types = self.TYPE_COMPATIBILITY.get(profile.data_type, set())

        if not compatible_types:
            logger.debug(f"DataTypeCompatibility: No compatible types for {profile.data_type}")
            return []

        mappings = []

        # Get all fields with compatible types
        for field_type in compatible_types:
            matching_keys = context.knowledge_base.lookup_by_type(field_type)

            for model_name, field_name in matching_keys:
                # Skip if we're filtering to specific models
                if context.target_models and model_name not in context.target_models:
                    continue
                if context.candidate_models and model_name not in context.candidate_models:
                    continue

                field = context.knowledge_base.get_field(model_name, field_name)
                if not field:
                    continue

                # Calculate confidence based on type compatibility strength
                confidence = self._calculate_type_confidence(
                    profile.data_type,
                    field.field_type
                )

                rationale = (
                    f"Data type compatibility: column type '{profile.data_type}' is compatible "
                    f"with field type '{field.field_type}'"
                )

                scores = {
                    "type_compatible": 1.0 if field.field_type in compatible_types else 0.0,
                    "type_confidence": confidence,
                    "column_type": profile.data_type,
                    "field_type": field.field_type,
                }

                mapping = self.create_mapping(
                    field=field,
                    confidence=confidence,
                    rationale=rationale,
                    scores=scores,
                    source_column=column_name,
                )

                mappings.append(mapping)

        logger.info(
            f"DataTypeCompatibility: Found {len(mappings)} compatible fields "
            f"for type '{profile.data_type}'"
        )

        return self.sort_by_confidence(mappings)

    def _calculate_type_confidence(
        self,
        column_type: str,
        field_type: str
    ) -> float:
        """
        Calculate confidence score for a specific type pairing.

        Args:
            column_type: Detected column data type
            field_type: Odoo field type

        Returns:
            Confidence score from 0.0 to 1.0
        """
        # Perfect matches get highest confidence
        perfect_matches = {
            ("integer", "integer"): 0.95,
            ("float", "float"): 0.95,
            ("float", "monetary"): 0.90,
            ("boolean", "boolean"): 0.95,
            ("date", "date"): 0.95,
            ("date", "datetime"): 0.90,
        }

        key = (column_type, field_type)
        if key in perfect_matches:
            return perfect_matches[key]

        # Good matches
        good_matches = {
            ("integer", "float"): 0.85,
            ("integer", "many2one"): 0.80,
            ("string", "char"): 0.85,
            ("string", "text"): 0.85,
            ("string", "selection"): 0.80,
            ("string", "many2one"): 0.75,
        }

        if key in good_matches:
            return good_matches[key]

        # Acceptable matches (fallback to char/text)
        if field_type in ("char", "text"):
            return 0.60

        # Generic compatibility
        return 0.50
