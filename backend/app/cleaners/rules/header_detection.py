"""
Header detection rule.

Finds the actual header row in a spreadsheet, skipping metadata rows.
"""
import pandas as pd
from typing import Optional
import logging

from ..base import CleaningRule, CleaningResult, ChangeType
from ..config import CleaningConfig


logger = logging.getLogger(__name__)


class HeaderDetectionRule(CleaningRule):
    """
    Detects the header row in a DataFrame and drops metadata rows.

    Many spreadsheet exports include metadata rows before the actual headers
    (e.g., "Exported on 2025-10-06", company info, etc.). This rule identifies
    the header row using heuristics and drops everything before it.
    """

    def __init__(self, config: CleaningConfig):
        self.config = config

    @property
    def name(self) -> str:
        return "Header Detection"

    @property
    def priority(self) -> int:
        return 10  # Run first!

    @property
    def description(self) -> str:
        return "Detect header row and skip metadata rows"

    def clean(self, df: pd.DataFrame) -> CleaningResult:
        """
        Find the header row and drop metadata rows above it.

        Args:
            df: Input DataFrame (with no headers set, all integer column names)

        Returns:
            CleaningResult with headers properly set
        """
        result = CleaningResult(df=df.copy())

        # If config specifies explicit header row, use it
        if self.config.header_detection_method != "auto":
            if self.config.header_detection_method.startswith("row_"):
                try:
                    row_num = int(self.config.header_detection_method.split("_")[1])
                    return self._use_explicit_header(df, row_num, result)
                except (ValueError, IndexError):
                    result.add_warning(f"Invalid header_detection_method: {self.config.header_detection_method}, falling back to auto")

        # Auto-detect header row
        header_row = self._detect_header_row(df)

        if header_row is None:
            # Couldn't detect, assume row 0
            result.add_warning("Could not detect header row, assuming row 0")
            header_row = 0

        logger.info(f"Detected header row: {header_row}")

        # Drop rows before header
        if header_row > 0:
            result.add_change(
                ChangeType.ROW_DROPPED,
                f"Dropped {header_row} metadata rows before header",
                {"rows_dropped": header_row, "rows": list(range(header_row))}
            )
            result.stats["metadata_rows_dropped"] = header_row

        # Set the header row
        df_clean = df.iloc[header_row+1:].copy()  # Data starts after header row
        df_clean.columns = df.iloc[header_row].values  # Set column names from header row

        # Reset index
        df_clean = df_clean.reset_index(drop=True)

        result.df = df_clean
        result.add_change(
            ChangeType.HEADER_DETECTION,
            f"Set header from row {header_row}",
            {"header_row": header_row, "column_count": len(df_clean.columns)}
        )
        result.stats["header_row"] = header_row
        result.stats["final_column_count"] = len(df_clean.columns)

        return result

    def _detect_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """
        Detect which row is the header using heuristics.

        Args:
            df: DataFrame to analyze

        Returns:
            Row index of header, or None if can't detect
        """
        max_rows = min(self.config.max_rows_to_check, len(df))
        scores = []

        for i in range(max_rows):
            score = self._score_row_as_header(df, i)
            scores.append((i, score))
            logger.debug(f"Row {i} score: {score:.2f}")

        # Return row with highest score (if score > threshold)
        scores.sort(key=lambda x: x[1], reverse=True)
        best_row, best_score = scores[0]

        # Threshold: must score at least 50 to be considered a header
        if best_score < 50:
            return None

        return best_row

    def _score_row_as_header(self, df: pd.DataFrame, row_idx: int) -> float:
        """
        Score a row based on how likely it is to be a header.

        Higher score = more likely to be header.

        Args:
            df: DataFrame
            row_idx: Row index to score

        Returns:
            Score (0-100+)
        """
        row = df.iloc[row_idx]
        score = 0.0

        # Factor 1: Non-null percentage (headers should be mostly non-null)
        non_null_pct = row.notna().sum() / len(row)
        if non_null_pct > 0.8:
            score += 40  # Very complete row
        elif non_null_pct > 0.5:
            score += 20  # Reasonably complete
        elif non_null_pct < 0.1:
            score -= 50  # Probably not a header (metadata row often has 1-2 values)

        # Factor 2: String values (headers are usually strings)
        string_count = sum(1 for v in row if isinstance(v, str))
        string_pct = string_count / row.notna().sum() if row.notna().sum() > 0 else 0
        if string_pct > 0.9:
            score += 30  # Mostly strings
        elif string_pct > 0.7:
            score += 15
        elif string_pct < 0.3:
            score -= 20  # Not enough strings

        # Factor 3: Average length (headers are usually 5-50 chars)
        non_null_vals = row.dropna()
        if len(non_null_vals) > 0:
            avg_length = sum(len(str(v)) for v in non_null_vals) / len(non_null_vals)
            if 5 <= avg_length <= 50:
                score += 20  # Good header length
            elif avg_length > 100:
                score -= 20  # Too long (might be metadata)
            elif avg_length < 3:
                score -= 10  # Too short (might be data)

        # Factor 4: Metadata indicators (negative score)
        row_str = ' '.join(str(v) for v in non_null_vals if pd.notna(v)).lower()
        metadata_keywords = ['exported', 'generated', 'report date', 'created on', '©', 'copyright']
        if any(keyword in row_str for keyword in metadata_keywords):
            score -= 40  # Definitely metadata

        # Factor 5: Duplicate values (headers should be mostly unique)
        if len(non_null_vals) > 0:
            unique_pct = len(set(str(v) for v in non_null_vals)) / len(non_null_vals)
            if unique_pct > 0.9:
                score += 15  # Very unique
            elif unique_pct < 0.5:
                score -= 15  # Too many duplicates

        # Factor 6: Position bias (headers are usually in first few rows)
        if row_idx == 0:
            score += 10  # Slight preference for row 0
        elif row_idx == 1:
            score += 5  # Also common
        elif row_idx > 5:
            score -= 10  # Less likely to be header

        return score

    def _use_explicit_header(self, df: pd.DataFrame, row_num: int, result: CleaningResult) -> CleaningResult:
        """Use explicitly specified header row."""
        if row_num >= len(df):
            result.add_warning(f"Specified header row {row_num} exceeds DataFrame length {len(df)}, using row 0")
            row_num = 0

        # Drop rows before header
        if row_num > 0:
            result.add_change(
                ChangeType.ROW_DROPPED,
                f"Dropped {row_num} rows before explicitly specified header",
                {"rows_dropped": row_num}
            )

        # Set header
        df_clean = df.iloc[row_num+1:].copy()
        df_clean.columns = df.iloc[row_num].values
        df_clean = df_clean.reset_index(drop=True)

        result.df = df_clean
        result.add_change(
            ChangeType.HEADER_DETECTION,
            f"Used explicitly specified header row {row_num}",
            {"header_row": row_num}
        )
        result.stats["header_row"] = row_num
        result.stats["explicit"] = True

        return result
