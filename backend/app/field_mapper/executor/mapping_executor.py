"""
MappingExecutor - Executes field mappings to transform data.

This module applies field mappings to actual data, performing transformations
and preparing data for Odoo import.
"""
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

from ..core.data_structures import FieldMapping, DataTransformation, MappingResult
from ..core.knowledge_base import OdooKnowledgeBase
from ..config.logging_config import setup_logger

logger = setup_logger(__name__)


class MappingExecutor:
    """
    Executes field mappings to transform spreadsheet data into Odoo-compatible format.

    This class:
    1. Applies field mappings to DataFrames
    2. Performs data transformations
    3. Validates data against Odoo constraints
    4. Generates Odoo-compatible output
    """

    def __init__(self, knowledge_base: OdooKnowledgeBase):
        """
        Initialize the mapping executor.

        Args:
            knowledge_base: OdooKnowledgeBase for field definitions
        """
        self.knowledge_base = knowledge_base
        logger.info("MappingExecutor initialized")

    def execute_mappings(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, List[FieldMapping]],
        target_model: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Execute mappings on a DataFrame.

        Args:
            df: Source DataFrame
            mappings: Dictionary mapping column names to FieldMapping lists
            target_model: Optional target model to filter mappings

        Returns:
            Transformed DataFrame with Odoo field names
        """
        logger.info(f"Executing mappings on DataFrame with {len(df)} rows")

        result_data = {}

        for source_column, field_mappings in mappings.items():
            if source_column not in df.columns:
                logger.warning(f"Source column '{source_column}' not found in DataFrame")
                continue

            if not field_mappings:
                logger.warning(f"No mappings for column '{source_column}'")
                continue

            # Use the best (first) mapping
            best_mapping = field_mappings[0]

            # Filter by target model if specified
            if target_model and best_mapping.target_model != target_model:
                continue

            # Get source data
            source_data = df[source_column]

            # Apply transformations
            transformed_data = self._apply_transformations(
                source_data,
                best_mapping
            )

            # Use target field name as column name
            target_field = best_mapping.target_field or source_column
            result_data[target_field] = transformed_data

            logger.debug(
                f"Mapped '{source_column}' -> '{target_field}' "
                f"({best_mapping.target_model})"
            )

        # Create result DataFrame
        result_df = pd.DataFrame(result_data)

        logger.info(f"Execution complete: {len(result_df.columns)} columns mapped")

        return result_df

    def execute_by_model(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, List[FieldMapping]]
    ) -> Dict[str, pd.DataFrame]:
        """
        Execute mappings grouped by target model.

        Args:
            df: Source DataFrame
            mappings: Dictionary mapping column names to FieldMapping lists

        Returns:
            Dictionary mapping model names to transformed DataFrames
        """
        logger.info("Executing mappings grouped by model")

        # Group mappings by target model
        model_mappings: Dict[str, Dict[str, List[FieldMapping]]] = {}

        for source_column, field_mappings in mappings.items():
            if not field_mappings:
                continue

            best_mapping = field_mappings[0]
            model_name = best_mapping.target_model

            if model_name not in model_mappings:
                model_mappings[model_name] = {}

            model_mappings[model_name][source_column] = field_mappings

        # Execute mappings for each model
        results = {}

        for model_name, model_specific_mappings in model_mappings.items():
            logger.info(f"Processing model: {model_name}")
            result_df = self.execute_mappings(
                df,
                model_specific_mappings,
                target_model=model_name
            )
            results[model_name] = result_df

        logger.info(f"Execution complete: {len(results)} models")

        return results

    def _apply_transformations(
        self,
        data: pd.Series,
        mapping: FieldMapping
    ) -> pd.Series:
        """
        Apply transformations to a data series.

        Args:
            data: Source data series
            mapping: FieldMapping with transformation instructions

        Returns:
            Transformed data series
        """
        transformed = data.copy()

        if not mapping.transformations:
            return transformed

        for transformation in mapping.transformations:
            logger.debug(f"Applying transformation: {transformation.type}")

            try:
                if transformation.type == "type_cast":
                    transformed = self._transform_type_cast(transformed, transformation)
                elif transformation.type == "date_format":
                    transformed = self._transform_date_format(transformed, transformation)
                elif transformation.type == "string_clean":
                    transformed = self._transform_string_clean(transformed, transformation)
                elif transformation.type == "boolean_convert":
                    transformed = self._transform_boolean_convert(transformed, transformation)
                elif transformation.type == "numeric_convert":
                    transformed = self._transform_numeric_convert(transformed, transformation)
                elif transformation.type == "selection_map":
                    transformed = self._transform_selection_map(transformed, transformation)
                else:
                    logger.warning(f"Unknown transformation type: {transformation.type}")

            except Exception as e:
                logger.error(
                    f"Error applying transformation {transformation.type}: {e}",
                    exc_info=True
                )

        return transformed

    def _transform_type_cast(
        self,
        data: pd.Series,
        transformation: DataTransformation
    ) -> pd.Series:
        """
        Cast data to a specific type.

        Args:
            data: Source data
            transformation: Transformation with target type

        Returns:
            Transformed data
        """
        target_type = transformation.parameters.get("target_type", "str")

        if target_type == "int":
            return pd.to_numeric(data, errors="coerce").astype("Int64")
        elif target_type == "float":
            return pd.to_numeric(data, errors="coerce")
        elif target_type == "str":
            return data.astype(str)
        elif target_type == "bool":
            return data.astype(bool)
        else:
            logger.warning(f"Unknown target type: {target_type}")
            return data

    def _transform_date_format(
        self,
        data: pd.Series,
        transformation: DataTransformation
    ) -> pd.Series:
        """
        Transform date format.

        Args:
            data: Source data
            transformation: Transformation with date format

        Returns:
            Transformed data
        """
        source_format = transformation.parameters.get("source_format")
        target_format = transformation.parameters.get("target_format", "%Y-%m-%d")

        # Parse dates
        if source_format:
            parsed = pd.to_datetime(data, format=source_format, errors="coerce")
        else:
            parsed = pd.to_datetime(data, errors="coerce")

        # Format dates
        return parsed.dt.strftime(target_format)

    def _transform_string_clean(
        self,
        data: pd.Series,
        transformation: DataTransformation
    ) -> pd.Series:
        """
        Clean string data.

        Args:
            data: Source data
            transformation: Transformation with cleaning options

        Returns:
            Transformed data
        """
        cleaned = data.astype(str)

        if transformation.parameters.get("strip", True):
            cleaned = cleaned.str.strip()

        if transformation.parameters.get("lowercase", False):
            cleaned = cleaned.str.lower()

        if transformation.parameters.get("uppercase", False):
            cleaned = cleaned.str.upper()

        return cleaned

    def _transform_boolean_convert(
        self,
        data: pd.Series,
        transformation: DataTransformation
    ) -> pd.Series:
        """
        Convert to boolean.

        Args:
            data: Source data
            transformation: Transformation with boolean mapping

        Returns:
            Transformed data
        """
        true_values = transformation.parameters.get(
            "true_values",
            ["true", "yes", "1", "t", "y"]
        )
        false_values = transformation.parameters.get(
            "false_values",
            ["false", "no", "0", "f", "n"]
        )

        def convert_bool(val):
            if pd.isna(val):
                return None
            str_val = str(val).lower().strip()
            if str_val in true_values:
                return True
            elif str_val in false_values:
                return False
            else:
                return None

        return data.apply(convert_bool)

    def _transform_numeric_convert(
        self,
        data: pd.Series,
        transformation: DataTransformation
    ) -> pd.Series:
        """
        Convert to numeric, handling currency symbols, etc.

        Args:
            data: Source data
            transformation: Transformation parameters

        Returns:
            Transformed data
        """
        # Remove currency symbols and formatting
        cleaned = data.astype(str).str.replace(r"[$€£¥,]", "", regex=True)

        # Convert to numeric
        numeric = pd.to_numeric(cleaned, errors="coerce")

        # Apply scaling if specified
        scale = transformation.parameters.get("scale", 1.0)
        if scale != 1.0:
            numeric = numeric * scale

        return numeric

    def _transform_selection_map(
        self,
        data: pd.Series,
        transformation: DataTransformation
    ) -> pd.Series:
        """
        Map values to selection options.

        Args:
            data: Source data
            transformation: Transformation with value mapping

        Returns:
            Transformed data
        """
        value_map = transformation.parameters.get("value_map", {})

        if not value_map:
            return data

        # Apply mapping (case-insensitive)
        def map_value(val):
            if pd.isna(val):
                return None
            str_val = str(val).lower().strip()
            return value_map.get(str_val, val)

        return data.apply(map_value)

    def generate_odoo_import_csv(
        self,
        df: pd.DataFrame,
        model_name: str,
        output_path: str
    ) -> None:
        """
        Generate an Odoo-compatible CSV import file.

        Args:
            df: Transformed DataFrame
            model_name: Target Odoo model
            output_path: Path to save CSV file
        """
        logger.info(f"Generating Odoo import CSV for model '{model_name}'")

        # Add model name column if not present
        if "model" not in df.columns:
            df = df.copy()
            df.insert(0, "model", model_name)

        # Save to CSV
        df.to_csv(output_path, index=False)

        logger.info(f"Odoo import CSV saved to: {output_path}")

    def generate_odoo_import_dict(
        self,
        df: pd.DataFrame,
        model_name: str
    ) -> List[Dict[str, Any]]:
        """
        Generate Odoo-compatible dictionary records.

        Args:
            df: Transformed DataFrame
            model_name: Target Odoo model

        Returns:
            List of dictionaries ready for Odoo API
        """
        logger.info(f"Generating Odoo import dictionaries for model '{model_name}'")

        records = []

        for idx, row in df.iterrows():
            record = {"model": model_name}

            for col_name, value in row.items():
                # Skip null values
                if pd.isna(value):
                    continue

                # Add to record
                record[col_name] = value

            records.append(record)

        logger.info(f"Generated {len(records)} Odoo records")

        return records

    def validate_mappings(
        self,
        df: pd.DataFrame,
        mappings: Dict[str, List[FieldMapping]]
    ) -> List[str]:
        """
        Validate that mappings can be executed on the DataFrame.

        Args:
            df: Source DataFrame
            mappings: Field mappings

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for source_column, field_mappings in mappings.items():
            # Check column exists
            if source_column not in df.columns:
                errors.append(f"Column '{source_column}' not found in DataFrame")
                continue

            # Check mappings exist
            if not field_mappings:
                errors.append(f"No mappings for column '{source_column}'")
                continue

            # Check confidence threshold
            best_mapping = field_mappings[0]
            if best_mapping.confidence < 0.5:
                errors.append(
                    f"Low confidence mapping for '{source_column}': "
                    f"{best_mapping.confidence:.2f}"
                )

        return errors
