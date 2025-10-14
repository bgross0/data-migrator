"""
Whitespace cleaning rule implemented for Polars DataFrames.

Trims leading/trailing whitespace from all text values and optionally
normalises internal spacing.
"""
from __future__ import annotations

import logging
from typing import Optional

import polars as pl

from ..base import ChangeType, CleaningResult, CleaningRule
from ..config import CleaningConfig

logger = logging.getLogger(__name__)


class WhitespaceRule(CleaningRule):
    """
    Trim whitespace from string columns.

    Mirrors the previous pandas-based behaviour while working with Polars.
    """

    def __init__(self, config: CleaningConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "Whitespace Trimming"

    @property
    def priority(self) -> int:
        return 30  # After header and column name cleaning

    @property
    def description(self) -> str:
        return "Trim leading/trailing whitespace from all text values"

    def clean(self, df: pl.DataFrame) -> CleaningResult:
        """
        Trim whitespace from all string columns.

        Args:
            df: Input Polars DataFrame

        Returns:
            CleaningResult with trimmed values
        """
        result = CleaningResult(df=df.clone())

        columns_cleaned = 0
        values_cleaned = 0

        for column_name in result.df.columns:
            column = result.df[column_name]

            if column.dtype not in (pl.Utf8, pl.String):
                continue

            non_null_mask = column.is_not_null()
            if not bool(non_null_mask.any()):
                continue

            trimmed = column.str.strip_chars()
            if self.config.normalize_internal_spaces:
                trimmed = trimmed.str.replace_all(r"\s+", " ")

            # Identify actual changes (ignoring nulls)
            changed_mask = non_null_mask & (column != trimmed)
            changed = int(changed_mask.sum())
            if changed == 0:
                continue

            columns_cleaned += 1
            values_cleaned += changed

            result.df = result.df.with_columns(trimmed.alias(column_name))
            result.add_change(
                ChangeType.VALUE_MODIFIED,
                f"Trimmed whitespace in column '{column_name}'",
                {"column": column_name, "values_modified": changed},
            )
            logger.debug(
                "Trimmed whitespace in %s values for column '%s'",
                changed,
                column_name,
            )

        result.stats["columns_cleaned"] = columns_cleaned
        result.stats["values_cleaned"] = values_cleaned
        result.stats["total_columns"] = len(result.df.columns)

        if values_cleaned > 0:
            logger.info(
                "Trimmed whitespace from %s values across %s columns",
                values_cleaned,
                columns_cleaned,
            )
        else:
            logger.info("No whitespace issues detected")

        return result
