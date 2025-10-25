"""
Column profiling engine - analyzes spreadsheet columns for data types, quality metrics, patterns.
Updated to use Polars instead of pandas for better performance.

Uses centralized TypeRegistry for all type detection and parsing.
"""
import polars as pl
import pandas as pd  # Still needed for Excel reading until Polars adds native support
import re
from typing import Dict, List, Any
from pathlib import Path

# Import centralized type system
from app.core.type_system import TypeRegistry, TypeParseError

# Import detection services
from app.services.column_signature import ColumnSignatureDetector
from app.services.polymorphic_detector import PolymorphicDetector
from app.services.pivot_service import PivotDetector


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
        column_names = df.columns

        # Prepare sample data for detectors (first 100 rows as dicts)
        sample_data = df.head(100).to_dicts()

        # Run entity detection on all columns
        entity_detector = ColumnSignatureDetector()
        entity_signatures = entity_detector.detect_entity_type(column_names, sample_data)

        # Run polymorphic detection
        polymorphic_detector = PolymorphicDetector()
        polymorphic_signatures = polymorphic_detector.detect_polymorphic_columns(column_names, sample_data)

        # Run pivot detection
        pivot_detector = PivotDetector()
        pivot_groups = pivot_detector.detect_pivot_groups(column_names)

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
                # Add detection results
                "detected_entity": [
                    {
                        "entity_type": sig.entity_type,
                        "confidence": sig.confidence,
                        "matched_columns": sig.matched_columns
                    }
                    for sig in entity_signatures
                ] if entity_signatures else None,
                "polymorphic_signature": [
                    {
                        "model_col": sig.model_col,
                        "id_col": sig.id_col,
                        "confidence": sig.confidence,
                        "detected_models": sig.detected_models,
                        "inference": sig.inference
                    }
                    for sig in polymorphic_signatures
                ] if polymorphic_signatures else None,
                "pivot_group": [
                    {
                        "prefix": grp.prefix,
                        "indices": grp.indices,
                        "confidence": grp.confidence,
                        "target_entity": grp.target_entity
                    }
                    for grp in pivot_groups
                ] if pivot_groups else None,
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
        """Infer specific type for string columns using centralized TypeRegistry."""
        # Drop nulls for analysis
        series_clean = series.drop_nulls()

        if series_clean.len() == 0:
            return "string"

        # Get unique values as strings
        unique_vals = set(str(v).lower() for v in series_clean.unique().to_list())

        # Check boolean
        if unique_vals.issubset({'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}):
            return "boolean"

        # Try parsing as datetime using TypeRegistry
        # Sample first 10 values to avoid expensive parsing
        sample = series_clean.head(10).to_list()
        date_success = 0
        for val in sample:
            try:
                if TypeRegistry.parse_date(val):
                    date_success += 1
            except TypeParseError:
                pass

        if date_success / len(sample) > 0.7:  # 70% threshold
            return "date"

        # Try parsing as currency/numeric using TypeRegistry
        numeric_success = 0
        for val in sample:
            try:
                if TypeRegistry.parse_currency(val) is not None:
                    numeric_success += 1
            except TypeParseError:
                pass

        if numeric_success / len(sample) > 0.7:  # 70% threshold
            return "float"

        return "string"

    def detect_patterns(self, series: pl.Series) -> Dict[str, float]:
        """
        Detect common patterns in a column using centralized TypeRegistry.

        Uses actual parsing validation instead of just regex to ensure
        patterns match what DataCleaner can actually process.
        """
        patterns = {}

        # Convert to string and drop nulls
        series_clean = series.drop_nulls().cast(pl.Utf8)

        if series_clean.len() == 0:
            return patterns

        total = series_clean.len()
        values = series_clean.to_list()

        # Email pattern - validate using TypeRegistry
        email_matches = 0
        for val in values:
            try:
                if TypeRegistry.parse_email(val):
                    email_matches += 1
            except TypeParseError:
                pass
        if email_matches > 0:
            patterns['email'] = float(email_matches / total)

        # Phone pattern - validate using TypeRegistry
        phone_matches = 0
        for val in values:
            try:
                if TypeRegistry.parse_phone(val, default_region='US'):
                    phone_matches += 1
            except TypeParseError:
                pass
        if phone_matches > 0:
            patterns['phone'] = float(phone_matches / total)

        # Currency pattern - validate using TypeRegistry
        currency_matches = 0
        for val in values:
            try:
                if TypeRegistry.parse_currency(val) is not None:
                    currency_matches += 1
            except TypeParseError:
                pass
        if currency_matches > 0:
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