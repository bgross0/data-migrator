"""
Lambda transformation engine extracted from odoo-etl.
Handles lambda transformations for field mappings using Polars.

Based on odoo-etl/models/etl.py lines 564-579
"""

from __future__ import annotations

import ast
import logging
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, Optional

import polars as pl

logger = logging.getLogger(__name__)

SAFE_BUILTINS = {
    "len": len,
    "max": max,
    "min": min,
    "sum": sum,
    "abs": abs,
    "round": round,
    "sorted": sorted,
    "any": any,
    "all": all,
    "bool": bool,
    "int": int,
    "float": float,
    "str": str,
}

POLARS_DTYPE_LOOKUP = {
    "pl.Int8": pl.Int8,
    "pl.Int16": pl.Int16,
    "pl.Int32": pl.Int32,
    "pl.Int64": pl.Int64,
    "pl.UInt8": pl.UInt8,
    "pl.UInt16": pl.UInt16,
    "pl.UInt32": pl.UInt32,
    "pl.UInt64": pl.UInt64,
    "pl.Float32": pl.Float32,
    "pl.Float64": pl.Float64,
    "pl.Boolean": pl.Boolean,
    "pl.Utf8": pl.Utf8,
    "pl.String": pl.String,
    "pl.Datetime": pl.Datetime,
    "pl.Date": pl.Date,
    "int": pl.Int64,
    "float": pl.Float64,
    "str": pl.Utf8,
    "bool": pl.Boolean,
}


class LambdaTransformer:
    """
    Executes lambda transformations on Polars DataFrames.
    Adapted from odoo-etl's implementation with additional safety guards.
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
        **kwargs: Any,
    ) -> pl.DataFrame:
        """
        Apply a lambda transformation to create a new column.

        This follows the odoo-etl pattern but constrains execution to a
        safe subset of Python built-ins and infers Polars dtypes when possible.

        Args:
            data: Source Polars DataFrame
            target_field: Name for the new column
            lambda_func: Lambda function (string or callable)
            data_type: Optional Polars type (string) to cast result to
            **kwargs: Additional arguments passed to lambda

        Returns:
            DataFrame with new column added
        """
        callable_lambda = self._prepare_lambda(lambda_func)

        def wrapper(row: Dict[str, Any]) -> Any:
            """Execute lambda, supporting odoo-etl signature variants."""
            try:
                return callable_lambda(self, row, **kwargs)
            except TypeError:
                return callable_lambda(row)

        target_dtype = self._resolve_dtype(data_type) if data_type else None

        if target_dtype is None:
            inferred_dtype = self._infer_result_dtype(wrapper, data)
            target_dtype = inferred_dtype

        if target_dtype is not None:
            mapped_series = pl.struct(pl.all()).map_elements(
                wrapper,
                return_dtype=target_dtype,
            )
        else:
            mapped_series = pl.struct(pl.all()).map_elements(wrapper)

        result = data.with_columns(mapped_series.alias(target_field))

        # Explicit cast if a target dtype was provided but map_elements fell back.
        if data_type:
            resolved = self._resolve_dtype(data_type)
            if resolved is None:
                raise ValueError(f"Unsupported Polars dtype string: {data_type}")
            result = result.with_columns(
                pl.col(target_field).cast(resolved, strict=False)
            )

        return result

    def _prepare_lambda(self, lambda_func: Any) -> Callable[..., Any]:
        """Compile or validate the provided lambda."""
        if callable(lambda_func):
            return lambda_func

        if not isinstance(lambda_func, str):
            raise TypeError("lambda_func must be a callable or lambda expression string")

        source = " ".join(lambda_func.strip().split())
        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Invalid lambda expression: {exc}") from exc

        if not isinstance(tree.body, ast.Lambda):
            raise ValueError("Only lambda expressions are allowed for lambda mappings")

        compiled = compile(tree, "<lambda>", "eval")
        safe_globals = {
            "__builtins__": SAFE_BUILTINS,
            "pl": pl,
            "datetime": datetime,
            "Decimal": Decimal,
            **self.context,
        }
        return eval(compiled, safe_globals, {})

    def _resolve_dtype(self, dtype_name: Optional[str]) -> Optional[pl.datatypes.DataType]:
        """Resolve a dtype string to a Polars dtype."""
        if not dtype_name:
            return None
        name = dtype_name.strip()
        if name in POLARS_DTYPE_LOOKUP:
            return POLARS_DTYPE_LOOKUP[name]
        # Allow matching without prefix, e.g., "Utf8"
        prefixed_name = f"pl.{name}" if not name.startswith("pl.") else name
        return POLARS_DTYPE_LOOKUP.get(prefixed_name)

    def _infer_result_dtype(
        self,
        fn: Callable[[Dict[str, Any]], Any],
        data: pl.DataFrame,
    ) -> Optional[pl.datatypes.DataType]:
        """Infer output dtype by sampling a few rows."""
        for row in self._iter_sample_rows(data, sample_size=5):
            try:
                value = fn(row)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Lambda preview failed during dtype inference: %s", exc)
                continue
            if value is None:
                continue
            return self._map_python_value_to_dtype(value)
        return None

    @staticmethod
    def _iter_sample_rows(
        data: pl.DataFrame,
        sample_size: int = 5,
    ) -> Iterable[Dict[str, Any]]:
        """Yield up to `sample_size` rows as dictionaries."""
        if data.is_empty():
            return []
        preview = data.head(sample_size)
        return preview.to_dicts()

    @staticmethod
    def _map_python_value_to_dtype(value: Any) -> Optional[pl.datatypes.DataType]:
        """Map a Python value to an appropriate Polars dtype."""
        if isinstance(value, bool):
            return pl.Boolean
        if isinstance(value, int) and not isinstance(value, bool):
            return pl.Int64
        if isinstance(value, float):
            return pl.Float64
        if isinstance(value, Decimal):
            return pl.Float64
        if isinstance(value, datetime):
            return pl.Datetime
        if isinstance(value, str):
            return pl.Utf8
        return None

    def apply_field_mappings(
        self,
        data: pl.DataFrame,
        field_mappings: Dict[str, Dict[str, Any]],
        **kwargs: Any,
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
            mapping_type = mapping.get("type", "column")

            if mapping_type == "column":
                column_name = mapping.get("column_name")
                if column_name and column_name in data.columns:
                    resolved_dtype = self._resolve_dtype(mapping.get("data_type"))
                    if resolved_dtype:
                        result = result.with_columns(
                            data[column_name].cast(resolved_dtype, strict=False).alias(target_field)
                        )
                    else:
                        result = result.with_columns(
                            data[column_name].alias(target_field)
                        )

            elif mapping_type == "lambda":
                lambda_func = mapping.get("function")
                if lambda_func:
                    result = self.apply_lambda_mapping(
                        data if result.is_empty() else result,
                        target_field,
                        lambda_func,
                        mapping.get("data_type"),
                        **kwargs,
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
