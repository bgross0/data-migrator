"""
Column Profiler for analyzing spreadsheet columns.

This module provides functionality to profile columns from uploaded spreadsheets,
detecting data types, patterns, statistical properties, and more.

Now using Polars for better performance.
"""
import re
from typing import List, Dict, Any, Optional
from collections import Counter
import polars as pl
from datetime import datetime

from ..core.data_structures import ColumnProfile
from ..config.logging_config import profiling_logger as logger


class ColumnProfiler:
    """
    Profiles columns from spreadsheets to extract metadata for field matching.

    This class analyzes columns to determine:
    - Data types (string, integer, float, boolean, date)
    - Patterns (email, phone, URL, currency, date formats)
    - Statistical properties (min, max, mean, median for numeric)
    - Uniqueness ratio
    - Value frequency distribution
    - Null/empty value ratio
    """

    # Pattern definitions
    PATTERNS = {
        "email": re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            re.IGNORECASE
        ),
        "phone": re.compile(
            r"^[\+\(\)\s\-\d]{7,20}$"  # Flexible phone pattern
        ),
        "url": re.compile(
            r"^https?://[^\s]+$",
            re.IGNORECASE
        ),
        "currency": re.compile(
            r"^[\$\€\£\¥]?\s*\d+([,\.]\d{3})*([,\.]\d{2})?$"
        ),
        "date_iso": re.compile(
            r"^\d{4}-\d{2}-\d{2}$"  # YYYY-MM-DD
        ),
        "date_us": re.compile(
            r"^\d{1,2}/\d{1,2}/\d{2,4}$"  # M/D/YYYY or MM/DD/YYYY
        ),
        "date_eu": re.compile(
            r"^\d{1,2}\.\d{1,2}\.\d{2,4}$"  # D.M.YYYY or DD.MM.YYYY
        ),
    }

    def __init__(self, sample_size: int = 1000):
        """
        Initialize the profiler.

        Args:
            sample_size: Maximum number of rows to sample for pattern detection
        """
        self.sample_size = sample_size
        logger.info(f"ColumnProfiler initialized with sample_size={sample_size}")

    def profile_column(
        self,
        column_name: str,
        data: pl.Series,
        sheet_name: str = "Sheet1"
    ) -> ColumnProfile:
        """
        Profile a single column from a spreadsheet.

        Args:
            column_name: Name of the column
            data: Polars Series containing the column data
            sheet_name: Name of the sheet this column belongs to

        Returns:
            ColumnProfile object with all detected metadata
        """
        logger.info(f"Profiling column: {column_name} (sheet: {sheet_name})")

        # Remove null values for analysis
        clean_data = data.drop_nulls()
        total_rows = len(data)
        non_null_rows = len(clean_data)

        # Handle empty columns
        if non_null_rows == 0:
            logger.warning(f"Column '{column_name}' is entirely null")
            return ColumnProfile(
                column_name=column_name,
                sheet_name=sheet_name,
                data_type="null",
                sample_values=[],
                total_rows=total_rows,
                non_null_count=0,
                unique_count=0,
                null_percentage=100.0,
                uniqueness_ratio=0.0,
                patterns={},
                value_frequencies={},
            )

        # Sample the data if it's too large
        if non_null_rows > self.sample_size:
            sample_data = clean_data.sample(n=self.sample_size, seed=42)
        else:
            sample_data = clean_data

        # Detect data type
        data_type = self._detect_data_type(sample_data)

        # Detect patterns
        patterns = self._detect_patterns(sample_data)

        # Calculate statistical properties
        min_value, max_value, mean_value, median_value = self._calculate_statistics(
            clean_data, data_type
        )

        # Calculate uniqueness ratio
        unique_count = clean_data.n_unique()
        uniqueness_ratio = float(unique_count) / non_null_rows

        # Get value frequencies (top 100 most common)
        value_freq = Counter(clean_data.head(1000).to_list())
        top_frequencies = dict(value_freq.most_common(100))

        # Get sample values (up to 10 unique values)
        sample_values = clean_data.unique().head(10).to_list()

        # Calculate null percentage
        null_percentage = ((total_rows - non_null_rows) / total_rows * 100) if total_rows > 0 else 0

        profile = ColumnProfile(
            column_name=column_name,
            sheet_name=sheet_name,
            data_type=data_type,
            sample_values=sample_values,
            total_rows=total_rows,
            non_null_count=non_null_rows,
            unique_count=unique_count,
            null_percentage=null_percentage,
            uniqueness_ratio=uniqueness_ratio,
            patterns=patterns,
            value_frequencies=top_frequencies,
            min_value=min_value,
            max_value=max_value,
        )

        logger.debug(
            f"Column '{column_name}' profile: type={data_type}, "
            f"patterns={list(patterns.keys())}, uniqueness={uniqueness_ratio:.2f}"
        )

        return profile

    def profile_dataframe(
        self,
        df: pl.DataFrame,
        sheet_name: str = "Sheet1"
    ) -> List[ColumnProfile]:
        """
        Profile all columns in a DataFrame.

        Args:
            df: Polars DataFrame to profile
            sheet_name: Name of the sheet

        Returns:
            List of ColumnProfile objects, one per column
        """
        logger.info(f"Profiling DataFrame with {len(df.columns)} columns")

        profiles = []
        for col_name in df.columns:
            try:
                profile = self.profile_column(col_name, df[col_name], sheet_name)
                profiles.append(profile)
            except Exception as e:
                logger.error(f"Error profiling column '{col_name}': {e}")

        logger.info(f"Successfully profiled {len(profiles)} columns")
        return profiles

    # ===========================
    # Data Type Detection
    # ===========================

    def _detect_data_type(self, data: pl.Series) -> str:
        """
        Detect the primary data type of a column.

        Args:
            data: Polars Series to analyze

        Returns:
            Data type as string: "integer", "float", "boolean", "date", "string"
        """
        # Check Polars dtype
        dtype = data.dtype

        if dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64]:
            return "integer"
        elif dtype in [pl.Float32, pl.Float64]:
            return "float"
        elif dtype == pl.Boolean:
            return "boolean"
        elif dtype in [pl.Date, pl.Datetime]:
            return "date"
        elif dtype == pl.Utf8:
            # Analyze string content
            unique_vals = set(str(v).lower() for v in data.unique().to_list() if v is not None)

            # Try to detect boolean
            if unique_vals.issubset({"true", "false", "yes", "no", "1", "0", "t", "f"}):
                return "boolean"

            # Try to parse as numeric
            try:
                data.cast(pl.Float64, strict=True)
                # Check if all values are integers
                numeric = data.cast(pl.Float64, strict=False).drop_nulls()
                if all(v == int(v) for v in numeric.to_list()):
                    return "integer"
                return "float"
            except:
                pass

            # Try to parse as date
            try:
                data.str.to_datetime()
                return "date"
            except:
                pass

            return "string"

        # Fallback
        return "string"

    # ===========================
    # Pattern Detection
    # ===========================

    def _detect_patterns(self, data: pl.Series) -> Dict[str, float]:
        """
        Detect patterns in the column data.

        Args:
            data: Polars Series to analyze

        Returns:
            Dictionary mapping pattern names to match ratios (0.0 to 1.0)
        """
        patterns_found: Dict[str, float] = {}

        # Convert all values to strings for pattern matching
        str_data = data.cast(pl.Utf8)

        # Test each pattern
        for pattern_name, pattern_re in self.PATTERNS.items():
            matches = str_data.map_elements(lambda x: bool(pattern_re.match(x)) if x else False, return_dtype=pl.Boolean)
            match_ratio = float(matches.sum()) / len(data)

            # Only include patterns with at least 20% match rate
            if match_ratio >= 0.2:
                patterns_found[pattern_name] = match_ratio

        # Consolidate date patterns
        date_patterns = {k: v for k, v in patterns_found.items() if k.startswith("date_")}
        if date_patterns:
            # Keep only the best matching date pattern
            best_date_pattern = max(date_patterns.items(), key=lambda x: x[1])
            patterns_found["date"] = best_date_pattern[1]
            # Remove individual date patterns
            for k in date_patterns.keys():
                del patterns_found[k]

        return patterns_found

    def _detect_email_pattern(self, data: pl.Series) -> float:
        """
        Detect email pattern in column data.

        Args:
            data: Polars Series to analyze

        Returns:
            Ratio of values matching email pattern (0.0 to 1.0)
        """
        str_data = data.cast(pl.Utf8)
        matches = str_data.map_elements(lambda x: bool(self.PATTERNS["email"].match(x)) if x else False, return_dtype=pl.Boolean)
        return float(matches.sum()) / len(data)

    def _detect_phone_pattern(self, data: pl.Series) -> float:
        """
        Detect phone number pattern in column data.

        Args:
            data: Polars Series to analyze

        Returns:
            Ratio of values matching phone pattern (0.0 to 1.0)
        """
        str_data = data.cast(pl.Utf8)
        matches = str_data.map_elements(lambda x: bool(self.PATTERNS["phone"].match(x)) if x else False, return_dtype=pl.Boolean)
        return float(matches.sum()) / len(data)

    def _detect_url_pattern(self, data: pl.Series) -> float:
        """
        Detect URL pattern in column data.

        Args:
            data: Polars Series to analyze

        Returns:
            Ratio of values matching URL pattern (0.0 to 1.0)
        """
        str_data = data.cast(pl.Utf8)
        matches = str_data.map_elements(lambda x: bool(self.PATTERNS["url"].match(x)) if x else False, return_dtype=pl.Boolean)
        return float(matches.sum()) / len(data)

    def _detect_currency_pattern(self, data: pl.Series) -> float:
        """
        Detect currency pattern in column data.

        Args:
            data: Polars Series to analyze

        Returns:
            Ratio of values matching currency pattern (0.0 to 1.0)
        """
        str_data = data.cast(pl.Utf8)
        matches = str_data.map_elements(lambda x: bool(self.PATTERNS["currency"].match(x)) if x else False, return_dtype=pl.Boolean)
        return float(matches.sum()) / len(data)

    def _detect_date_pattern(self, data: pl.Series) -> float:
        """
        Detect date pattern in column data.

        Args:
            data: Polars Series to analyze

        Returns:
            Ratio of values matching any date pattern (0.0 to 1.0)
        """
        str_data = data.cast(pl.Utf8)

        # Try all date patterns
        total_matches = 0
        for pattern_name in ["date_iso", "date_us", "date_eu"]:
            pattern = self.PATTERNS[pattern_name]
            matches = str_data.map_elements(lambda x: bool(pattern.match(x)) if x else False, return_dtype=pl.Boolean)
            total_matches = max(total_matches, float(matches.sum()))

        return total_matches / len(data)

    # ===========================
    # Statistical Analysis
    # ===========================

    def _calculate_statistics(
        self,
        data: pl.Series,
        data_type: str
    ) -> tuple[Optional[Any], Optional[Any], Optional[float], Optional[float]]:
        """
        Calculate statistical properties for numeric columns.

        Args:
            data: Polars Series to analyze
            data_type: Detected data type

        Returns:
            Tuple of (min_value, max_value, mean_value, median_value)
        """
        if data_type not in ["integer", "float"]:
            return None, None, None, None

        try:
            numeric_data = data.cast(pl.Float64, strict=False).drop_nulls()

            if len(numeric_data) == 0:
                return None, None, None, None

            min_val = float(numeric_data.min())
            max_val = float(numeric_data.max())
            mean_val = float(numeric_data.mean())
            median_val = float(numeric_data.median())

            return min_val, max_val, mean_val, median_val

        except Exception as e:
            logger.warning(f"Error calculating statistics: {e}")
            return None, None, None, None

    def _calculate_uniqueness_ratio(self, data: pl.Series) -> float:
        """
        Calculate the uniqueness ratio of a column.

        Args:
            data: Polars Series to analyze

        Returns:
            Ratio of unique values to total values (0.0 to 1.0)
        """
        clean_data = data.drop_nulls()
        if len(clean_data) == 0:
            return 0.0

        return clean_data.n_unique() / len(clean_data)

    def _analyze_value_frequencies(
        self,
        data: pl.Series,
        top_n: int = 100
    ) -> Dict[Any, int]:
        """
        Analyze value frequency distribution.

        Args:
            data: Polars Series to analyze
            top_n: Number of top values to return

        Returns:
            Dictionary mapping values to their frequencies
        """
        clean_data = data.drop_nulls()
        value_counts = clean_data.value_counts().head(top_n)
        return {row[0]: row[1] for row in value_counts.iter_rows()}

    # ===========================
    # Utility Methods
    # ===========================

    def get_profile_summary(self, profile: ColumnProfile) -> str:
        """
        Get a human-readable summary of a column profile.

        Args:
            profile: ColumnProfile to summarize

        Returns:
            String summary
        """
        summary_parts = [
            f"Column: {profile.column_name}",
            f"Type: {profile.data_type}",
            f"Non-null rows: {profile.non_null_count}/{profile.total_rows}",
            f"Uniqueness: {profile.uniqueness_ratio:.2%}",
        ]

        if profile.patterns:
            pattern_str = ", ".join(
                f"{k}={v:.0%}" for k, v in profile.patterns.items()
            )
            summary_parts.append(f"Patterns: {pattern_str}")

        if profile.min_value is not None:
            summary_parts.append(
                f"Range: [{profile.min_value}, {profile.max_value}]"
            )

        if profile.mean_value is not None:
            summary_parts.append(
                f"Mean: {profile.mean_value:.2f}, Median: {profile.median_value:.2f}"
            )

        return " | ".join(summary_parts)
