"""
Column name cleaning rule.

Cleans column names to improve matching by removing parentheses,
special characters, and normalizing whitespace.
"""
from __future__ import annotations

import logging
import re
from typing import List

import polars as pl

from ..base import ChangeType, CleaningResult, CleaningRule
from ..config import CleaningConfig


logger = logging.getLogger(__name__)


class ColumnNameCleaningRule(CleaningRule):
    """
    Cleans column names for better matching.

    Removes common issues like:
    - Parenthetical suffixes: " (Contact)", " (Opp)", " (All)"
    - Special characters: *, ?, #, ...
    - Extra whitespace
    """

    def __init__(self, config: CleaningConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "Column Name Cleaning"

    @property
    def priority(self) -> int:
        return 20  # After header detection, before data cleaning

    @property
    def description(self) -> str:
        return "Clean column names by removing parentheses, special chars, and extra whitespace"

    def clean(self, df: pl.DataFrame) -> CleaningResult:
        """
        Clean column names.

        Args:
            df: Input DataFrame

        Returns:
            CleaningResult with cleaned column names
        """
        result = CleaningResult(df=df.clone())

        original_columns = result.df.columns
        cleaned_columns: List[str] = []
        changes_made = 0

        for col in original_columns:
            cleaned = self._clean_column_name(str(col))

            if cleaned != str(col):
                changes_made += 1
                result.add_change(
                    ChangeType.COLUMN_RENAMED,
                    "Renamed column",
                    {"old_name": str(col), "new_name": cleaned},
                )
                logger.debug(f"Renamed column: '{col}' → '{cleaned}'")

            cleaned_columns.append(cleaned)

        # Check for duplicates after cleaning
        if len(cleaned_columns) != len(set(cleaned_columns)):
            cleaned_columns = self._handle_duplicates(cleaned_columns, result)

        rename_map = dict(zip(original_columns, cleaned_columns))
        result.df = result.df.rename(rename_map)

        result.stats["columns_renamed"] = changes_made
        result.stats["original_column_count"] = len(original_columns)
        result.stats["final_column_count"] = len(cleaned_columns)

        if changes_made > 0:
            logger.info(f"Cleaned {changes_made}/{len(original_columns)} column names")

        return result

    def _clean_column_name(self, name: str) -> str:
        """
        Clean a single column name.

        Args:
            name: Original column name

        Returns:
            Cleaned column name
        """
        cleaned = name

        # Step 1: Remove parentheses and contents if enabled
        if self.config.remove_parentheses:
            cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)

        # Step 2: Remove trailing special characters if enabled
        if self.config.remove_special_chars:
            chars = re.escape(self.config.special_chars_to_remove)
            cleaned = re.sub(rf"[{chars}\.]+$", "", cleaned)
            cleaned = cleaned.replace("?", "")

        # Step 3: Trim whitespace
        if self.config.trim_column_names:
            cleaned = cleaned.strip()

        # Step 4: Normalize spaces if enabled
        if self.config.normalize_spaces:
            cleaned = re.sub(r"\s+", " ", cleaned)

        if not cleaned or cleaned.isspace():
            cleaned = "Unnamed"

        return cleaned

    def _handle_duplicates(self, columns: List[str], result: CleaningResult) -> List[str]:
        """
        Handle duplicate column names by adding suffixes.

        Args:
            columns: List of column names (may have duplicates)
            result: CleaningResult to add warnings to

        Returns:
            List with unique column names
        """
        seen = {}
        unique_columns: List[str] = []

        for col in columns:
            if col not in seen:
                seen[col] = 0
                unique_columns.append(col)
            else:
                seen[col] += 1
                new_name = f"{col}_{seen[col] + 1}"
                unique_columns.append(new_name)

                result.add_warning(f"Duplicate column name '{col}' renamed to '{new_name}'")
                result.add_change(
                    ChangeType.COLUMN_RENAMED,
                    "Resolved duplicate column name",
                    {"original": col, "renamed_to": new_name, "occurrence": seen[col] + 1},
                )

        return unique_columns
