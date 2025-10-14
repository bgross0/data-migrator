"""
Column profiling engine - analyzes spreadsheet columns for data types, quality metrics, patterns.
Updated to use Polars instead of pandas for better performance.
"""
import polars as pl
import pandas as pd  # Still needed for Excel reading until Polars adds native support
import re
from typing import Dict, List, Any
from pathlib import Path


class ColumnProfiler:
    """Profiles columns in a spreadsheet to determine data types, quality, and patterns."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def profile(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Profile all sheets and columns in the file.

        Returns:
            Dict mapping sheet names to list of column profiles
        """
        results = {}

        # Read file based on extension
        if self.file_path.suffix.lower() in ['.xlsx', '.xls']:
            # Excel file - use pandas to read then convert to Polars
            excel_file = pd.ExcelFile(self.file_path)
            for sheet_name in excel_file.sheet_names:
                df_pandas = pd.read_excel(excel_file, sheet_name=sheet_name)
                # Convert all columns to string to avoid PyArrow type errors
                # Let Polars infer types properly after conversion
                df_pandas = df_pandas.astype(str)
                # Convert to Polars with string schema
                df = pl.from_pandas(df_pandas, schema_overrides={col: pl.Utf8 for col in df_pandas.columns})
                results[sheet_name] = self._profile_dataframe(df)
        elif self.file_path.suffix.lower() == '.csv':
            # CSV file - read directly with Polars
            df = pl.read_csv(
                self.file_path,
                try_parse_dates=True,
                ignore_errors=True,
                truncate_ragged_lines=True
            )
            results['Sheet1'] = self._profile_dataframe(df)
        else:
            raise ValueError(f"Unsupported file format: {self.file_path.suffix}")

        return results

    def _profile_dataframe(self, df: pl.DataFrame) -> List[Dict[str, Any]]:
        """Profile all columns in a Polars dataframe."""
        profiles = []
        n_rows = df.height  # Polars uses .height instead of len()

        for col_name in df.columns:
            series = df[col_name]

            # Basic stats using Polars methods
            null_count = series.null_count()
            null_pct = null_count / n_rows if n_rows > 0 else 0
            distinct_count = series.n_unique()
            distinct_pct = distinct_count / n_rows if n_rows > 0 else 0

            # Detect dtype
            dtype = self.detect_dtype(series)

            # Detect patterns
            patterns = self.detect_patterns(series)

            # Get sample values (first 10 unique non-null)
            # Polars approach
            sample_values = series.drop_nulls().unique().head(10).to_list()

            # Convert to JSON-serializable types
            sample_values = [
                bool(v) if isinstance(v, bool) else
                str(v) if v is not None and not isinstance(v, (int, float, str)) else
                v
                for v in sample_values
            ]

            profiles.append({
                "name": str(col_name),
                "dtype": dtype,
                "null_pct": float(null_pct),
                "distinct_pct": float(distinct_pct),
                "patterns": patterns,
                "sample_values": sample_values,
                "n_rows": n_rows,
            })

        return profiles

    def detect_dtype(self, series: pl.Series) -> str:
        """Detect the data type of a Polars Series."""
        # Get Polars dtype
        polars_dtype = series.dtype

        # Map Polars dtypes to our types
        if polars_dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64]:
            return "integer"
        elif polars_dtype in [pl.Float32, pl.Float64]:
            return "float"
        elif polars_dtype == pl.Boolean:
            return "boolean"
        elif polars_dtype in [pl.Date, pl.Datetime, pl.Time]:
            return "date"
        elif polars_dtype in [pl.Utf8, pl.String]:
            # For string types, try to infer more specific types
            return self._infer_string_type(series)

        return "string"

    def _infer_string_type(self, series: pl.Series) -> str:
        """Infer specific type for string columns."""
        # Drop nulls for analysis
        series_clean = series.drop_nulls()

        if series_clean.len() == 0:
            return "string"

        # Get unique values as strings
        unique_vals = set(str(v).lower() for v in series_clean.unique().to_list())

        # Check boolean
        if unique_vals.issubset({'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}):
            return "boolean"

        # Try parsing as datetime
        try:
            # Attempt to parse as datetime
            series_clean.str.to_datetime()
            return "date"
        except:
            pass

        # Try parsing as numeric
        try:
            # Remove currency symbols and commas
            cleaned = series_clean.str.replace_all(r'[$,]', '')
            cleaned.cast(pl.Float64)
            return "float"
        except:
            pass

        return "string"

    def detect_patterns(self, series: pl.Series) -> Dict[str, float]:
        """Detect common patterns in a column (email, phone, etc.)."""
        patterns = {}

        # Convert to string and drop nulls
        series_clean = series.drop_nulls().cast(pl.Utf8)

        if series_clean.len() == 0:
            return patterns

        total = series_clean.len()

        # Email pattern
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        email_matches = series_clean.str.contains(email_pattern).sum()
        if email_matches and email_matches > 0:
            patterns['email'] = float(email_matches / total)

        # Phone pattern (US format, simple)
        phone_pattern = r'^\+?1?\s*\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}$'
        phone_matches = series_clean.str.contains(phone_pattern).sum()
        if phone_matches and phone_matches > 0:
            patterns['phone'] = float(phone_matches / total)

        # Currency pattern
        currency_pattern = r'^\$?\s?[0-9,]+(\.[0-9]{2})?$'
        currency_matches = series_clean.str.contains(currency_pattern).sum()
        if currency_matches and currency_matches > 0:
            patterns['currency'] = float(currency_matches / total)

        return patterns

    def _detect_data_type(self, series: pl.Series) -> str:
        """Detect the data type of a series."""
        # Get basic Polars dtype
        dtype = series.dtype

        # Convert to string for analysis
        if dtype == pl.String:
            return "string"
        elif dtype == pl.Int64:
            return "integer" 
        elif dtype == pl.Float64:
            return "float"
        elif dtype == pl.Boolean:
            return "boolean"
        elif dtype == pl.Date:
            return "date"
        elif dtype == pl.Datetime:
            return "datetime"
        elif dtype == pl.Duration:
            return "duration"
        elif dtype == pl.Categorical:
            return "categorical"
        else:
            return "string"  # Default to string for unknown types