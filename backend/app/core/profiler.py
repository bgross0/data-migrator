"""
Column profiling engine - analyzes spreadsheet columns for data types, quality metrics, patterns.
"""
import pandas as pd
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
            # Excel file - read all sheets
            excel_file = pd.ExcelFile(self.file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                results[sheet_name] = self._profile_dataframe(df)
        elif self.file_path.suffix.lower() == '.csv':
            # CSV file - single sheet
            df = pd.read_csv(self.file_path)
            results['Sheet1'] = self._profile_dataframe(df)
        else:
            raise ValueError(f"Unsupported file format: {self.file_path.suffix}")

        return results

    def _profile_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Profile all columns in a dataframe."""
        profiles = []
        n_rows = len(df)

        for col_name in df.columns:
            series = df[col_name]

            # Basic stats
            null_count = series.isna().sum()
            null_pct = null_count / n_rows if n_rows > 0 else 0
            distinct_count = series.nunique()
            distinct_pct = distinct_count / n_rows if n_rows > 0 else 0

            # Detect dtype
            dtype = self.detect_dtype(series)

            # Detect patterns
            patterns = self.detect_patterns(series)

            # Get sample values (first 10 unique non-null)
            sample_values = series.dropna().unique()[:10].tolist()

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

    def detect_dtype(self, series: pd.Series) -> str:
        """Detect the data type of a pandas Series."""
        # Drop nulls for analysis
        series_clean = series.dropna()

        if len(series_clean) == 0:
            return "string"

        # Check pandas dtype first
        if pd.api.types.is_integer_dtype(series):
            return "integer"
        elif pd.api.types.is_float_dtype(series):
            return "float"
        elif pd.api.types.is_bool_dtype(series):
            return "boolean"
        elif pd.api.types.is_datetime64_any_dtype(series):
            return "date"

        # For object types, try to infer
        # Try boolean
        unique_vals = set(str(v).lower() for v in series_clean.unique())
        if unique_vals.issubset({'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}):
            return "boolean"

        # Try date
        try:
            pd.to_datetime(series_clean, errors='raise')
            return "date"
        except (ValueError, TypeError):
            pass

        # Try numeric
        try:
            pd.to_numeric(series_clean, errors='raise')
            return "float"
        except (ValueError, TypeError):
            pass

        return "string"

    def detect_patterns(self, series: pd.Series) -> Dict[str, float]:
        """Detect common patterns in a column (email, phone, etc.)."""
        patterns = {}
        series_clean = series.dropna().astype(str)

        if len(series_clean) == 0:
            return patterns

        total = len(series_clean)

        # Email pattern
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        email_matches = series_clean.str.match(email_pattern).sum()
        if email_matches > 0:
            patterns['email'] = float(email_matches / total)

        # Phone pattern (US format, simple)
        phone_pattern = r'^\+?1?\s*\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}$'
        phone_matches = series_clean.str.match(phone_pattern).sum()
        if phone_matches > 0:
            patterns['phone'] = float(phone_matches / total)

        # Currency pattern
        currency_pattern = r'^\$?\s?[0-9,]+(\.[0-9]{2})?$'
        currency_matches = series_clean.str.match(currency_pattern).sum()
        if currency_matches > 0:
            patterns['currency'] = float(currency_matches / total)

        return patterns
