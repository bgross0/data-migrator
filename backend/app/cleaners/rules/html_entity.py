"""
HTML entity decoding rule.

Decodes HTML entities like &amp;, &lt;, &gt; to their actual characters.
"""
import html
import logging
from typing import Callable

import polars as pl

from ..base import CleaningRule, CleaningResult, ChangeType
from ..config import CleaningConfig


logger = logging.getLogger(__name__)

_HTML_ENTITY_PATTERN = r"&[a-zA-Z]+;|&#\d+;"


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

    def _decode_fn(self) -> Callable[[str], str]:
        """Return a decoder function bound once for map_elements."""
        return lambda value: html.unescape(value) if value is not None else None

    def clean(self, df: pl.DataFrame) -> CleaningResult:
        """
        Decode HTML entities in all string columns.

        Args:
            df: Input Polars DataFrame

        Returns:
            CleaningResult with decoded values
        """
        result = CleaningResult(df=df.clone())

        columns_cleaned = 0
        values_cleaned = 0
        decoder = self._decode_fn()

        for column_name in result.df.columns:
            column = result.df[column_name]

            if column.dtype not in (pl.Utf8, pl.String):
                continue

            # Identify candidate rows containing HTML entities
            contains_entities = (
                column.str.contains(_HTML_ENTITY_PATTERN)
                .fill_null(False)
            )

            entity_count = int(contains_entities.sum())
            if entity_count == 0:
                continue

            # Decode entities and count actual changes
            decoded = column.map_elements(decoder, return_dtype=pl.Utf8)
            changed_mask = (
                column.is_not_null()
                & decoded.is_not_null()
                & (column != decoded)
            )
            changed = int(changed_mask.sum())

            if changed == 0:
                continue

            columns_cleaned += 1
            values_cleaned += changed

            result.df = result.df.with_columns(
                decoded.alias(column_name)
            )

            result.add_change(
                ChangeType.VALUE_MODIFIED,
                f"Decoded HTML entities in column '{column_name}'",
                {"column": column_name, "values_modified": changed},
            )
            logger.debug(
                "Decoded HTML entities in %s values for column '%s'",
                changed,
                column_name,
            )

        result.stats["columns_cleaned"] = columns_cleaned
        result.stats["values_cleaned"] = values_cleaned
        result.stats["total_columns"] = len(result.df.columns)

        if values_cleaned > 0:
            logger.info(
                "Decoded HTML entities in %s values across %s columns",
                values_cleaned,
                columns_cleaned,
            )
        else:
            logger.info("No HTML entities found")

        return result
