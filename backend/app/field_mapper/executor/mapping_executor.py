"""
MappingExecutor - Executes field mappings to transform data.

This module applies field mappings to actual data, performing transformations
and preparing data for Odoo import.

Updated to use Polars instead of pandas and support lambda transformations.
"""
from typing import Dict, List, Any, Optional
import polars as pl
import pandas as pd  # Keep for compatibility with other modules
from datetime import datetime

from ..core.data_structures import FieldMapping, DataTransformation, MappingResult
from ..core.knowledge_base import OdooKnowledgeBase
from ..config.logging_config import setup_logger

# Import our lambda transformer
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from app.core.lambda_transformer import LambdaTransformer

logger = setup_logger(__name__)


class MappingExecutor:
    """
    Executes field mappings to transform spreadsheet data into Odoo-compatible format.

    This class:
    1. Applies field mappings to DataFrames (now using Polars)
    2. Performs data transformations including lambdas
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
        self.lambda_transformer = LambdaTransformer()
        logger.info("MappingExecutor initialized with Polars support")

    def execute_mappings(
        self,
        df: pl.DataFrame,
        mappings: Dict[str, List[FieldMapping]],
        target_model: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Execute mappings on a Polars DataFrame.

        Args:
            df: Source DataFrame (Polars)
            mappings: Dictionary mapping column names to FieldMapping lists
            target_model: Optional target model to filter mappings

        Returns:
            Transformed DataFrame with Odoo field names
        """
        # Convert pandas DataFrame to Polars if needed
        if isinstance(df, pd.DataFrame):
            df = pl.from_pandas(df)

        logger.info(f"Executing mappings on DataFrame with {df.height} rows")

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

            # Check if this is a lambda mapping
            if hasattr(best_mapping, 'mapping_type') and best_mapping.mapping_type == 'lambda':
                # Use lambda transformer
                lambda_func = getattr(best_mapping, 'lambda_function', None)
                if lambda_func:
                    target_field = best_mapping.target_field or source_column
                    df = self.lambda_transformer.apply_lambda_mapping(
                        df,
                        target_field,
                        lambda_func,
                        getattr(best_mapping, 'data_type', None)
                    )
                    result_data[target_field] = df[target_field]
            else:
                # Regular column mapping
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

        # Create result DataFrame in Polars
        if result_data:
            # Build DataFrame from dictionary of series
            result_df = pl.DataFrame(result_data)
        else:
            result_df = pl.DataFrame()

        logger.info(f"Execution complete: {len(result_df.columns)} columns mapped")

        return result_df

    def execute_by_model(
        self,
        df: pl.DataFrame,
        mappings: Dict[str, List[FieldMapping]]
    ) -> Dict[str, pl.DataFrame]:
        """
        Execute mappings grouped by target model.

        Args:
            df: Source DataFrame (Polars)
            mappings: Dictionary mapping column names to FieldMapping lists

        Returns:
            Dictionary mapping model names to transformed DataFrames
        """
        # Convert pandas DataFrame to Polars if needed
        if isinstance(df, pd.DataFrame):
            df = pl.from_pandas(df)

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
        data: pl.Series,
        mapping: FieldMapping
    ) -> pl.Series:
        """
        Apply transformations to a Polars data series.

        Args:
            data: Source data series (Polars)
            mapping: FieldMapping with transformation instructions

        Returns:
            Transformed data series
        """
        transformed = data.clone()

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
        data: pl.Series,
        transformation: DataTransformation
    ) -> pl.Series:
        """
        Cast data to a specific type using Polars.

        Args:
            data: Source data (Polars Series)
            transformation: Transformation with target type

        Returns:
            Transformed data
        """
        target_type = transformation.parameters.get("target_type", "str")

        if target_type == "int":
            return data.cast(pl.Int64, strict=False)
        elif target_type == "float":
            return data.cast(pl.Float64, strict=False)
        elif target_type == "str":
            return data.cast(pl.Utf8)
        elif target_type == "bool":
            return data.cast(pl.Boolean)
        else:
            logger.warning(f"Unknown target type: {target_type}")
            return data

    def _transform_date_format(
        self,
        data: pl.Series,
        transformation: DataTransformation
    ) -> pl.Series:
        """
        Transform date format using Polars.

        Args:
            data: Source data (Polars Series)
            transformation: Transformation with date format

        Returns:
            Transformed data
        """
        target_format = transformation.parameters.get("target_format", "%Y-%m-%d")

        # Parse dates with Polars
        try:
            # Try to parse as datetime
            parsed = data.str.to_datetime()
            # Format dates
            return parsed.dt.strftime(target_format)
        except:
            logger.warning("Could not parse dates")
            return data

    def _transform_string_clean(
        self,
        data: pl.Series,
        transformation: DataTransformation
    ) -> pl.Series:
        """
        Clean string data using Polars.

        Args:
            data: Source data (Polars Series)
            transformation: Transformation with cleaning options

        Returns:
            Transformed data
        """
        cleaned = data.cast(pl.Utf8)

        if transformation.parameters.get("strip", True):
            cleaned = cleaned.str.strip_chars()

        if transformation.parameters.get("lowercase", False):
            cleaned = cleaned.str.to_lowercase()

        if transformation.parameters.get("uppercase", False):
            cleaned = cleaned.str.to_uppercase()

        return cleaned

    def _transform_boolean_convert(
        self,
        data: pl.Series,
        transformation: DataTransformation
    ) -> pl.Series:
        """
        Convert to boolean using Polars.

        Args:
            data: Source data (Polars Series)
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

        # Create boolean series using Polars expressions
        result = pl.Series([None] * data.len())

        for true_val in true_values:
            result = pl.when(data.cast(pl.Utf8).str.to_lowercase() == true_val).then(True).otherwise(result)

        for false_val in false_values:
            result = pl.when(data.cast(pl.Utf8).str.to_lowercase() == false_val).then(False).otherwise(result)

        return result

    def _transform_numeric_convert(
        self,
        data: pl.Series,
        transformation: DataTransformation
    ) -> pl.Series:
        """
        Convert to numeric using Polars, handling currency symbols, etc.

        Args:
            data: Source data (Polars Series)
            transformation: Transformation parameters

        Returns:
            Transformed data
        """
        # Remove currency symbols and formatting using Polars
        cleaned = data.cast(pl.Utf8).str.replace_all(r"[$€£¥,]", "")

        # Convert to numeric
        numeric = cleaned.cast(pl.Float64, strict=False)

        # Apply scaling if specified
        scale = transformation.parameters.get("scale", 1.0)
        if scale != 1.0:
            numeric = numeric * scale

        return numeric

    def _transform_selection_map(
        self,
        data: pl.Series,
        transformation: DataTransformation
    ) -> pl.Series:
        """
        Map values to selection options using Polars.

        Args:
            data: Source data (Polars Series)
            transformation: Transformation with value mapping

        Returns:
            Transformed data
        """
        value_map = transformation.parameters.get("value_map", {})

        if not value_map:
            return data

        # Apply mapping using Polars map_elements
        def map_value(val):
            if val is None:
                return None
            str_val = str(val).lower().strip()
            return value_map.get(str_val, val)

        return data.map_elements(map_value)

    def generate_odoo_import_csv(
        self,
        df: pl.DataFrame,
        model_name: str,
        output_path: str
    ) -> None:
        """
        Generate an Odoo-compatible CSV import file from Polars DataFrame.

        Args:
            df: Transformed DataFrame (Polars)
            model_name: Target Odoo model
            output_path: Path to save CSV file
        """
        logger.info(f"Generating Odoo import CSV for model '{model_name}'")

        # Add model name column if not present
        if "model" not in df.columns:
            df = df.with_columns(pl.lit(model_name).alias("model"))

        # Save to CSV using Polars
        df.write_csv(output_path)

        logger.info(f"Odoo import CSV saved to: {output_path}")

    def generate_odoo_import_dict(
        self,
        df: pl.DataFrame,
        model_name: str
    ) -> List[Dict[str, Any]]:
        """
        Generate Odoo-compatible dictionary records from Polars DataFrame.

        Args:
            df: Transformed DataFrame (Polars)
            model_name: Target Odoo model

        Returns:
            List of dictionaries ready for Odoo API
        """
        logger.info(f"Generating Odoo import dictionaries for model '{model_name}'")

        # Convert Polars DataFrame to list of dicts
        records = []
        for row in df.to_dicts():
            # Add model name
            row["model"] = model_name
            # Skip null values
            record = {k: v for k, v in row.items() if v is not None}
            records.append(record)

        logger.info(f"Generated {len(records)} Odoo records")

        return records

    def validate_mappings(
        self,
        df: pl.DataFrame,
        mappings: Dict[str, List[FieldMapping]]
    ) -> List[str]:
        """
        Validate that mappings can be executed on the Polars DataFrame.

        Args:
            df: Source DataFrame (Polars)
            mappings: Field mappings

        Returns:
            List of validation errors (empty if valid)
        """
        # Convert pandas DataFrame to Polars if needed
        if isinstance(df, pd.DataFrame):
            df = pl.from_pandas(df)

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