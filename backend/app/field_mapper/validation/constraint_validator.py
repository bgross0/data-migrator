"""
Constraint Validator for field mappings.

This module validates field mappings against Odoo constraints and field definitions.
"""
from typing import List, Dict, Set, Optional
import pandas as pd

from ..core.data_structures import (
    FieldMapping,
    ValidationResult,
    DataTransformation,
)
from ..core.knowledge_base import OdooKnowledgeBase
from ..config.logging_config import setup_logger

logger = setup_logger(__name__)


class ConstraintValidator:
    """
    Validates field mappings and data against Odoo constraints.

    This validator checks:
    1. Required fields are mapped
    2. Unique constraints are satisfied
    3. Type compatibility
    4. Selection value validity
    5. Relational field constraints
    """

    def __init__(self, knowledge_base: OdooKnowledgeBase):
        """
        Initialize the constraint validator.

        Args:
            knowledge_base: OdooKnowledgeBase for field and constraint information
        """
        self.knowledge_base = knowledge_base
        logger.info("ConstraintValidator initialized")

    def validate_mappings(
        self,
        mappings: Dict[str, List[FieldMapping]],
        target_model: str,
        df: Optional[pd.DataFrame] = None
    ) -> ValidationResult:
        """
        Validate field mappings for a target model.

        Args:
            mappings: Dictionary mapping column names to FieldMapping lists
            target_model: Target Odoo model
            df: Optional DataFrame with actual data for value validation

        Returns:
            ValidationResult with validation status and messages
        """
        logger.info(f"Validating mappings for model '{target_model}'")

        errors = []
        warnings = []
        suggestions = []

        # Filter mappings for target model
        model_mappings = self._filter_mappings_by_model(mappings, target_model)

        # Validate required fields
        req_errors, req_warnings = self._validate_required_fields(
            model_mappings,
            target_model
        )
        errors.extend(req_errors)
        warnings.extend(req_warnings)

        # Validate unique constraints
        uniq_errors, uniq_warnings = self._validate_unique_constraints(
            model_mappings,
            target_model,
            df
        )
        errors.extend(uniq_errors)
        warnings.extend(uniq_warnings)

        # Validate type compatibility
        type_errors, type_warnings, type_suggestions = self._validate_type_compatibility(
            model_mappings,
            df
        )
        errors.extend(type_errors)
        warnings.extend(type_warnings)
        suggestions.extend(type_suggestions)

        # Validate selection values
        sel_errors, sel_warnings, sel_suggestions = self._validate_selection_values(
            model_mappings,
            df
        )
        errors.extend(sel_errors)
        warnings.extend(sel_warnings)
        suggestions.extend(sel_suggestions)

        # Validate relational fields
        rel_errors, rel_warnings = self._validate_relational_fields(
            model_mappings
        )
        errors.extend(rel_errors)
        warnings.extend(rel_warnings)

        # Determine overall validity
        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validated_fields=list(model_mappings.keys()),
            missing_required_fields=self._get_missing_required_fields(
                model_mappings,
                target_model
            ),
        )

        logger.info(
            f"Validation complete: "
            f"valid={is_valid}, "
            f"errors={len(errors)}, "
            f"warnings={len(warnings)}"
        )

        return result

    def _filter_mappings_by_model(
        self,
        mappings: Dict[str, List[FieldMapping]],
        target_model: str
    ) -> Dict[str, FieldMapping]:
        """
        Filter mappings to only include those for the target model.

        Args:
            mappings: All mappings
            target_model: Target model name

        Returns:
            Dictionary mapping source columns to their best FieldMapping
        """
        filtered = {}

        for source_col, field_mappings in mappings.items():
            if not field_mappings:
                continue

            # Find best mapping for target model
            for mapping in field_mappings:
                if mapping.target_model == target_model:
                    filtered[source_col] = mapping
                    break

        return filtered

    def _validate_required_fields(
        self,
        mappings: Dict[str, FieldMapping],
        target_model: str
    ) -> tuple:
        """
        Validate that all required fields are mapped.

        Args:
            mappings: Filtered mappings for target model
            target_model: Target model name

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Get required fields for this model
        required_fields = self.knowledge_base.get_required_fields(target_model)

        # Get mapped field names
        mapped_fields = {mapping.target_field for mapping in mappings.values()}

        # Check for missing required fields
        missing_required = set(required_fields) - mapped_fields

        for field_name in missing_required:
            field = self.knowledge_base.get_field(target_model, field_name)
            if field:
                errors.append(
                    f"Required field '{field_name}' ({field.label}) is not mapped"
                )
            else:
                errors.append(f"Required field '{field_name}' is not mapped")

        return errors, warnings

    def _validate_unique_constraints(
        self,
        mappings: Dict[str, FieldMapping],
        target_model: str,
        df: Optional[pd.DataFrame]
    ) -> tuple:
        """
        Validate unique constraints.

        Args:
            mappings: Filtered mappings for target model
            target_model: Target model name
            df: Optional DataFrame with data

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Get unique constraints for this model
        unique_constraints = self.knowledge_base.get_unique_constraints(target_model)

        for constraint in unique_constraints:
            # Check if constrained fields are mapped
            # Note: constraint.fields might not be populated from Excel
            warnings.append(
                f"Model has unique constraint '{constraint.name}'. "
                f"Ensure mapped fields satisfy uniqueness requirements."
            )

        # If we have data, check for duplicate values in mapped fields
        if df is not None:
            for source_col, mapping in mappings.items():
                if source_col not in df.columns:
                    continue

                field = self.knowledge_base.get_field(
                    mapping.target_model,
                    mapping.target_field
                )

                if not field:
                    continue

                # Check if field should be unique (based on field name patterns)
                if any(pattern in field.name.lower() for pattern in ["id", "code", "ref", "reference"]):
                    # Check for duplicates
                    col_data = df[source_col].dropna()
                    if len(col_data) != len(col_data.unique()):
                        duplicates = col_data[col_data.duplicated()].unique()
                        warnings.append(
                            f"Field '{field.name}' appears to be a unique identifier "
                            f"but has {len(duplicates)} duplicate values"
                        )

        return errors, warnings

    def _validate_type_compatibility(
        self,
        mappings: Dict[str, FieldMapping],
        df: Optional[pd.DataFrame]
    ) -> tuple:
        """
        Validate type compatibility between source and target.

        Args:
            mappings: Filtered mappings
            df: Optional DataFrame with data

        Returns:
            Tuple of (errors, warnings, suggestions)
        """
        errors = []
        warnings = []
        suggestions = []

        for source_col, mapping in mappings.items():
            field = self.knowledge_base.get_field(
                mapping.target_model,
                mapping.target_field
            )

            if not field:
                continue

            # If we have data, validate actual values
            if df is not None and source_col in df.columns:
                col_data = df[source_col].dropna()

                if len(col_data) == 0:
                    continue

                # Check type-specific validations
                if field.field_type in ["integer", "float", "monetary"]:
                    # Check if values are numeric
                    non_numeric = []
                    for val in col_data.head(100):
                        try:
                            float(val)
                        except (ValueError, TypeError):
                            non_numeric.append(val)

                    if non_numeric:
                        warnings.append(
                            f"Field '{field.name}' expects numeric values "
                            f"but column '{source_col}' has non-numeric values: "
                            f"{non_numeric[:5]}"
                        )
                        suggestions.append(
                            DataTransformation(
                                type="numeric_convert",
                                description=f"Convert '{source_col}' to numeric",
                                parameters={"remove_symbols": True}
                            )
                        )

                elif field.field_type in ["date", "datetime"]:
                    # Check if values are dates
                    try:
                        pd.to_datetime(col_data.head(10))
                    except Exception:
                        warnings.append(
                            f"Field '{field.name}' expects date values "
                            f"but column '{source_col}' may not contain valid dates"
                        )
                        suggestions.append(
                            DataTransformation(
                                type="date_format",
                                description=f"Convert '{source_col}' to date format",
                                parameters={"target_format": "%Y-%m-%d"}
                            )
                        )

                elif field.field_type == "boolean":
                    # Check if values are boolean-like
                    unique_vals = set(str(v).lower() for v in col_data.unique()[:20])
                    bool_vals = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}

                    if not unique_vals.issubset(bool_vals):
                        warnings.append(
                            f"Field '{field.name}' expects boolean values "
                            f"but column '{source_col}' has non-boolean values"
                        )
                        suggestions.append(
                            DataTransformation(
                                type="boolean_convert",
                                description=f"Convert '{source_col}' to boolean",
                                parameters={}
                            )
                        )

        return errors, warnings, suggestions

    def _validate_selection_values(
        self,
        mappings: Dict[str, FieldMapping],
        df: Optional[pd.DataFrame]
    ) -> tuple:
        """
        Validate selection field values.

        Args:
            mappings: Filtered mappings
            df: Optional DataFrame with data

        Returns:
            Tuple of (errors, warnings, suggestions)
        """
        errors = []
        warnings = []
        suggestions = []

        for source_col, mapping in mappings.items():
            field = self.knowledge_base.get_field(
                mapping.target_model,
                mapping.target_field
            )

            if not field or field.field_type != "selection":
                continue

            # Get valid selection values
            valid_values = set(
                v.lower() for v in field.selection_values
            )

            if not valid_values:
                continue

            # If we have data, validate actual values
            if df is not None and source_col in df.columns:
                col_data = df[source_col].dropna()

                if len(col_data) == 0:
                    continue

                # Check for invalid values
                actual_values = set(str(v).lower().strip() for v in col_data.unique())
                invalid_values = actual_values - valid_values

                if invalid_values:
                    warnings.append(
                        f"Field '{field.name}' has invalid selection values in '{source_col}': "
                        f"{list(invalid_values)[:5]}. "
                        f"Valid values are: {list(valid_values)}"
                    )

                    # Suggest value mapping
                    value_map = {}
                    for invalid_val in invalid_values:
                        # Try to find close match
                        for valid_val in valid_values:
                            if invalid_val in valid_val or valid_val in invalid_val:
                                value_map[invalid_val] = valid_val
                                break

                    if value_map:
                        suggestions.append(
                            DataTransformation(
                                type="selection_map",
                                description=f"Map invalid values in '{source_col}'",
                                parameters={"value_map": value_map}
                            )
                        )

        return errors, warnings, suggestions

    def _validate_relational_fields(
        self,
        mappings: Dict[str, FieldMapping]
    ) -> tuple:
        """
        Validate relational fields (many2one, one2many, many2many).

        Args:
            mappings: Filtered mappings

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        for source_col, mapping in mappings.items():
            field = self.knowledge_base.get_field(
                mapping.target_model,
                mapping.target_field
            )

            if not field:
                continue

            if field.field_type in ["many2one", "one2many", "many2many"]:
                if not field.related_model:
                    warnings.append(
                        f"Relational field '{field.name}' has no related model defined"
                    )
                else:
                    warnings.append(
                        f"Field '{field.name}' is a {field.field_type} relation to '{field.related_model}'. "
                        f"Ensure source column '{source_col}' contains valid references."
                    )

        return errors, warnings

    def _get_missing_required_fields(
        self,
        mappings: Dict[str, FieldMapping],
        target_model: str
    ) -> List[str]:
        """
        Get list of missing required fields.

        Args:
            mappings: Filtered mappings
            target_model: Target model name

        Returns:
            List of missing required field names
        """
        required_fields = set(self.knowledge_base.get_required_fields(target_model))
        mapped_fields = {mapping.target_field for mapping in mappings.values()}

        return list(required_fields - mapped_fields)

    def suggest_transformations(
        self,
        mapping: FieldMapping,
        source_data: pd.Series
    ) -> List[DataTransformation]:
        """
        Suggest transformations for a specific field mapping.

        Args:
            mapping: FieldMapping to analyze
            source_data: Source data series

        Returns:
            List of suggested DataTransformation objects
        """
        suggestions = []

        field = self.knowledge_base.get_field(
            mapping.target_model,
            mapping.target_field
        )

        if not field:
            return suggestions

        # Type-based suggestions
        if field.field_type in ["integer", "float", "monetary"]:
            suggestions.append(
                DataTransformation(
                    type="numeric_convert",
                    description=f"Convert to {field.field_type}",
                    parameters={}
                )
            )

        elif field.field_type in ["date", "datetime"]:
            suggestions.append(
                DataTransformation(
                    type="date_format",
                    description="Convert to Odoo date format",
                    parameters={"target_format": "%Y-%m-%d"}
                )
            )

        elif field.field_type == "boolean":
            suggestions.append(
                DataTransformation(
                    type="boolean_convert",
                    description="Convert to boolean",
                    parameters={}
                )
            )

        # Always suggest string cleaning
        suggestions.append(
            DataTransformation(
                type="string_clean",
                description="Clean and trim string values",
                parameters={"strip": True}
            )
        )

        return suggestions
