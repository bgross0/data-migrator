"""
Whitespace cleaning rule.

Trims leading/trailing whitespace from all text values.
"""
import pandas as pd
import logging

from ..base import CleaningRule, CleaningResult, ChangeType
from ..config import CleaningConfig


logger = logging.getLogger(__name__)


class WhitespaceRule(CleaningRule):
    """
    Trims leading and trailing whitespace from all text values.

    Real-world spreadsheets often have inconsistent whitespace from copy-paste,
    data entry errors, or export formatting.
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

    def clean(self, df: pd.DataFrame) -> CleaningResult:
        """
        Trim whitespace from all string columns.

        Args:
            df: Input DataFrame

        Returns:
            CleaningResult with trimmed values
        """
        result = CleaningResult(df=df.copy())

        columns_cleaned = 0
        values_cleaned = 0

        # Process each column with object dtype (strings)
        for col in result.df.columns:
            if result.df[col].dtype == 'object':
                # Count values with whitespace issues before cleaning
                mask = result.df[col].notna()
                if mask.any():
                    before = result.df.loc[mask, col].astype(str)
                    after = before.str.strip()

                    # Count changes
                    changed = (before != after).sum()

                    if changed > 0:
                        result.df.loc[mask, col] = after
                        columns_cleaned += 1
                        values_cleaned += changed

                        result.add_change(
                            ChangeType.VALUE_MODIFIED,
                            f"Trimmed whitespace in column '{col}'",
                            {"column": col, "values_modified": changed}
                        )
                        logger.debug(f"Trimmed {changed} values in column '{col}'")

                    # Optional: Normalize internal spaces
                    if self.config.normalize_internal_spaces and changed > 0:
                        result.df.loc[mask, col] = result.df.loc[mask, col].str.replace(r'\s+', ' ', regex=True)

        result.stats["columns_cleaned"] = columns_cleaned
        result.stats["values_cleaned"] = values_cleaned
        result.stats["total_columns"] = len(result.df.columns)

        if values_cleaned > 0:
            logger.info(f"Trimmed whitespace from {values_cleaned} values across {columns_cleaned} columns")
        else:
            logger.info("No whitespace issues found")

        return result
