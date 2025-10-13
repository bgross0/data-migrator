"""
Lambda transformation engine extracted from odoo-etl.
Handles lambda transformations for field mappings using Polars.

Based on odoo-etl/models/etl.py lines 564-579
"""

import polars as pl
from typing import Dict, Any, Optional, Callable
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class LambdaTransformer:
    """
    Executes lambda transformations on Polars DataFrames.
    Adapted from odoo-etl's implementation.
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional context for lambda execution.

        Args:
            context: Dictionary of objects/functions available to lambdas
        """
        self.context = context or {}

    def apply_lambda_mapping(
        self,
        data: pl.DataFrame,
        target_field: str,
        lambda_func: Any,
        data_type: Optional[str] = None,
        **kwargs
    ) -> pl.DataFrame:
        """
        Apply a lambda transformation to create a new column.

        This is the exact pattern from odoo-etl lines 564-579:
        - Uses pl.struct(pl.all()) to pass entire row to lambda
        - Lambda receives (self, row, **kwargs)
        - Supports type casting after transformation

        Args:
            data: Source Polars DataFrame
            target_field: Name for the new column
            lambda_func: Lambda function (string or callable)
            data_type: Optional Polars type to cast result to
            **kwargs: Additional arguments passed to lambda

        Returns:
            DataFrame with new column added
        """

        # If lambda is a string, compile it
        if isinstance(lambda_func, str):
            # Create safe execution environment
            safe_globals = {
                'pl': pl,
                'datetime': datetime,
                **self.context
            }

            # Clean up multi-line lambdas
            lambda_func = lambda_func.strip()
            # Replace newlines and extra spaces in multi-line lambdas
            if '\n' in lambda_func:
                lambda_func = ' '.join(lambda_func.split())

            # Compile the lambda string
            exec(f"compiled_func = {lambda_func}", safe_globals)
            lambda_func = safe_globals['compiled_func']

        # Apply lambda using exact odoo-etl pattern (lines 565-570)
        # The lambda expects (self, row, **kwargs) in odoo-etl, but we support simple lambdas too
        def wrapper(row):
            try:
                # Try odoo-etl pattern first (self, row, **kwargs)
                return lambda_func(self, row, **kwargs)
            except TypeError:
                # Fall back to simple lambda (row) pattern
                return lambda_func(row)

        result = data.with_columns(
            data.select([
                pl.struct(pl.all()).map_elements(wrapper).alias(target_field)
            ]).to_series()
        )

        # Apply type casting if specified (lines 572-578)
        if data_type:
            if data_type == 'pl.Datetime':
                result = result.with_columns(
                    pl.col(target_field).str.to_datetime("%Y-%m-%d %H:%M:%S")
                )
            else:
                # Evaluate type string (e.g., "pl.Int64")
                result = result.with_columns(
                    pl.col(target_field).cast(eval(data_type))
                )

        return result

    def apply_field_mappings(
        self,
        data: pl.DataFrame,
        field_mappings: Dict[str, Dict],
        **kwargs
    ) -> pl.DataFrame:
        """
        Apply multiple field mappings including lambdas.

        Supports mapping types:
        - 'column': Direct column mapping
        - 'lambda': Lambda transformation

        Args:
            data: Source DataFrame
            field_mappings: Dict of field_name -> mapping config
            **kwargs: Additional context for lambdas

        Returns:
            Transformed DataFrame
        """
        result = pl.DataFrame()

        for target_field, mapping in field_mappings.items():
            mapping_type = mapping.get('type', 'column')

            if mapping_type == 'column':
                # Direct column mapping (lines 555-563)
                column_name = mapping.get('column_name')
                if column_name and column_name in data.columns:
                    if 'data_type' in mapping:
                        result = result.with_columns(
                            data[column_name].cast(eval(mapping['data_type'])).alias(target_field)
                        )
                    else:
                        result = result.with_columns(
                            data[column_name].alias(target_field)
                        )

            elif mapping_type == 'lambda':
                # Lambda transformation
                lambda_func = mapping.get('function')
                if lambda_func:
                    result = self.apply_lambda_mapping(
                        data if result.is_empty() else result,
                        target_field,
                        lambda_func,
                        mapping.get('data_type'),
                        **kwargs
                    )

        return result


# Example lambda functions that match odoo-etl patterns
EXAMPLE_LAMBDAS = {
    # Combine first and last name
    'full_name': {
        'type': 'lambda',
        'function': "lambda self, record, **kwargs: f\"{record['first_name']} {record['last_name']}\"",
    },

    # Format phone number
    'formatted_phone': {
        'type': 'lambda',
        'function': "lambda self, record, **kwargs: record['phone'].replace('-', '').replace(' ', '') if record['phone'] else ''",
    },

    # Calculate age from birthdate
    'age': {
        'type': 'lambda',
        'function': "lambda self, record, **kwargs: (datetime.now() - datetime.strptime(record['birthdate'], '%Y-%m-%d')).days // 365 if record['birthdate'] else None",
        'data_type': 'pl.Int64'
    },

    # Conditional field
    'customer_type': {
        'type': 'lambda',
        'function': "lambda self, record, **kwargs: 'Premium' if record.get('total_spent', 0) > 1000 else 'Regular'",
    },

    # Extract domain from email
    'email_domain': {
        'type': 'lambda',
        'function': "lambda self, record, **kwargs: record['email'].split('@')[1] if record.get('email') and '@' in record['email'] else None",
    }
}