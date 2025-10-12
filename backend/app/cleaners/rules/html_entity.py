"""
HTML entity decoding rule.

Decodes HTML entities like &amp;, &lt;, &gt; to their actual characters.
"""
import pandas as pd
import html
import logging

from ..base import CleaningRule, CleaningResult, ChangeType
from ..config import CleaningConfig


logger = logging.getLogger(__name__)


class HTMLEntityRule(CleaningRule):
    """
    Decodes HTML entities in text values.

    Common in data exported from web applications or CMS systems.
    Examples:
    - &amp; → &
    - &lt; → <
    - &gt; → >
    - &quot; → "
    - &#39; → '
    """

    def __init__(self, config: CleaningConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "HTML Entity Decoding"

    @property
    def priority(self) -> int:
        return 40  # After whitespace trimming

    @property
    def description(self) -> str:
        return "Decode HTML entities (&amp;, &lt;, etc.) to actual characters"

    def clean(self, df: pd.DataFrame) -> CleaningResult:
        """
        Decode HTML entities in all string columns.

        Args:
            df: Input DataFrame

        Returns:
            CleaningResult with decoded values
        """
        result = CleaningResult(df=df.copy())

        columns_cleaned = 0
        values_cleaned = 0

        # Process each column with object dtype (strings)
        for col in result.df.columns:
            if result.df[col].dtype == 'object':
                # Find values that contain HTML entities
                mask = result.df[col].notna()
                if mask.any():
                    # Check for common HTML entities
                    has_entities = result.df.loc[mask, col].astype(str).str.contains(
                        r'&[a-zA-Z]+;|&#\d+;',
                        regex=True,
                        na=False
                    )

                    if has_entities.any():
                        # Decode entities
                        before = result.df.loc[mask, col].astype(str)
                        after = before.apply(html.unescape)

                        # Count actual changes
                        changed = (before != after).sum()

                        if changed > 0:
                            result.df.loc[mask, col] = after
                            columns_cleaned += 1
                            values_cleaned += changed

                            result.add_change(
                                ChangeType.VALUE_MODIFIED,
                                f"Decoded HTML entities in column '{col}'",
                                {"column": col, "values_modified": changed}
                            )
                            logger.debug(f"Decoded HTML entities in {changed} values in column '{col}'")

        result.stats["columns_cleaned"] = columns_cleaned
        result.stats["values_cleaned"] = values_cleaned
        result.stats["total_columns"] = len(result.df.columns)

        if values_cleaned > 0:
            logger.info(f"Decoded HTML entities in {values_cleaned} values across {columns_cleaned} columns")
        else:
            logger.info("No HTML entities found")

        return result
