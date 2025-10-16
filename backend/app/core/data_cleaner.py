"""
Data cleaning engine - automatically cleans and standardizes spreadsheet data.

This module provides the DataCleaner class which applies intelligent cleaning
transformations based on detected column types and patterns.
"""
import polars as pl
import re
from typing import Dict, List, Any, Tuple
from datetime import datetime
import phonenumbers
from pathlib import Path


class DataCleaner:
    """
    Automatically cleans and standardizes spreadsheet data based on column profiles.

    Applies transformations like:
    - Trim whitespace from all text columns
    - Normalize phone numbers to E.164 format
    - Normalize emails (lowercase, strip)
    - Parse dates to ISO format
    - Strip currency symbols
    - Convert boolean strings to actual booleans
    - Convert empty strings to NULL
    """

    def __init__(self):
        """Initialize the data cleaner."""
        self.cleaning_report = {
            "total_rows": 0,
            "columns_cleaned": 0,
            "transformations": [],
            "errors": []
        }

    def clean_dataframe(
        self,
        df: pl.DataFrame,
        column_profiles: Dict[str, Dict[str, Any]],
        sheet_name: str = "Sheet1"
    ) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """
        Clean a dataframe based on column profiles.

        Args:
            df: Polars DataFrame to clean
            column_profiles: Dict of column metadata from profiling
                           {column_name: {"dtype": ..., "patterns": {...}, ...}}
            sheet_name: Name of the sheet being cleaned

        Returns:
            Tuple of (cleaned_df, cleaning_report)
        """
        self.cleaning_report["total_rows"] = df.height
        self.cleaning_report["sheet_name"] = sheet_name

        cleaned_df = df.clone()

        for col_name in df.columns:
            profile = column_profiles.get(col_name, {})
            dtype = profile.get("dtype", "string")
            patterns = profile.get("patterns", {})

            try:
                cleaned_df = self._clean_column(
                    cleaned_df,
                    col_name,
                    dtype,
                    patterns
                )
            except Exception as e:
                self.cleaning_report["errors"].append({
                    "column": col_name,
                    "error": str(e)
                })

        return cleaned_df, self.cleaning_report

    def _clean_column(
        self,
        df: pl.DataFrame,
        col_name: str,
        dtype: str,
        patterns: Dict[str, float]
    ) -> pl.DataFrame:
        """
        Apply appropriate cleaning transformations to a single column.

        Args:
            df: DataFrame
            col_name: Column name
            dtype: Detected data type
            patterns: Dict of pattern matches (e.g., {"email": 0.95, "phone": 0.1})

        Returns:
            DataFrame with cleaned column
        """
        transformations = []
        original_series = df[col_name]
        series = original_series

        # Convert to string for processing (we'll cast back later)
        if series.dtype != pl.Utf8:
            series = series.cast(pl.Utf8, strict=False)

        # 1. ALWAYS trim whitespace from text columns
        if dtype == "string" or dtype == "text":
            series_trimmed = series.str.strip_chars()
            if not series_trimmed.equals(series):
                series = series_trimmed
                transformations.append("trim_whitespace")

        # 2. Convert empty strings to NULL
        series_nullified = series.replace("", None)
        if not series_nullified.equals(series):
            series = series_nullified
            transformations.append("empty_to_null")

        # 3. Pattern-based cleaning (email, phone, etc.)
        email_pct = patterns.get("email", 0)
        phone_pct = patterns.get("phone", 0)
        currency_pct = patterns.get("currency", 0)

        # Email normalization (if >50% of values are emails)
        if email_pct > 0.5:
            series = self._normalize_emails(series)
            transformations.append("normalize_email")

        # Phone normalization (if >50% of values are phone numbers)
        elif phone_pct > 0.5:
            series = self._normalize_phones(series)
            transformations.append("normalize_phone")

        # Currency cleaning (if >50% of values are currency)
        elif currency_pct > 0.5:
            series = self._clean_currency(series)
            transformations.append("clean_currency")

        # 4. Data type specific cleaning
        elif dtype == "date" or dtype == "datetime":
            series = self._normalize_dates(series)
            transformations.append("normalize_date")

        elif dtype == "boolean":
            series = self._normalize_booleans(series)
            transformations.append("normalize_boolean")

        elif dtype == "integer" or dtype == "float":
            # Remove any non-numeric characters except . and -
            series = series.str.replace_all(r"[^\d.-]", "")
            transformations.append("clean_numeric")

        # Update DataFrame with cleaned column
        if transformations:
            df = df.with_columns(series.alias(col_name))

            self.cleaning_report["columns_cleaned"] += 1
            self.cleaning_report["transformations"].append({
                "column": col_name,
                "dtype": dtype,
                "patterns": patterns,
                "transformations": transformations
            })

        return df

    def _normalize_emails(self, series: pl.Series) -> pl.Series:
        """
        Normalize email addresses.

        - Convert to lowercase
        - Strip whitespace
        - Keep NULL as NULL
        """
        return series.str.to_lowercase().str.strip_chars()

    def _normalize_phones(self, series: pl.Series) -> pl.Series:
        """
        Normalize phone numbers to E.164 format when possible.

        Falls back to original if parsing fails.
        """
        def normalize_phone(value):
            if not value:
                return None
            try:
                # Try parsing with US as default country
                parsed = phonenumbers.parse(str(value), "US")
                if phonenumbers.is_valid_number(parsed):
                    return phonenumbers.format_number(
                        parsed,
                        phonenumbers.PhoneNumberFormat.E164
                    )
                return str(value)  # Return original if invalid
            except:
                return str(value)  # Return original if parsing fails

        return series.map_elements(normalize_phone, return_dtype=pl.Utf8)

    def _clean_currency(self, series: pl.Series) -> pl.Series:
        """
        Clean currency values by removing $, commas, and other symbols.

        Returns numeric string suitable for float conversion.
        """
        # Remove currency symbols and commas
        return series.str.replace_all(r"[$,€£¥]", "").str.strip_chars()

    def _normalize_dates(self, series: pl.Series) -> pl.Series:
        """
        Normalize dates to ISO format (YYYY-MM-DD).

        Attempts to parse various date formats and standardize.
        """
        def parse_date(value):
            if not value:
                return None
            try:
                # Try common date formats
                for fmt in [
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                    "%m-%d-%Y",
                    "%d-%m-%Y",
                    "%Y/%m/%d",
                    "%b %d, %Y",
                    "%B %d, %Y",
                    "%d %b %Y",
                    "%d %B %Y",
                ]:
                    try:
                        parsed = datetime.strptime(str(value).strip(), fmt)
                        return parsed.strftime("%Y-%m-%d")
                    except:
                        continue

                # If all formats fail, return original
                return str(value)
            except:
                return str(value)

        return series.map_elements(parse_date, return_dtype=pl.Utf8)

    def _normalize_booleans(self, series: pl.Series) -> pl.Series:
        """
        Normalize boolean strings to lowercase true/false.

        Converts: yes/no, y/n, 1/0, true/false → true/false
        """
        def parse_bool(value):
            if not value:
                return None

            val = str(value).lower().strip()

            if val in ["yes", "y", "true", "t", "1"]:
                return "true"
            elif val in ["no", "n", "false", "f", "0"]:
                return "false"
            else:
                return val  # Keep original if not recognized

        return series.map_elements(parse_bool, return_dtype=pl.Utf8)

    def get_cleaning_summary(self) -> str:
        """
        Get a human-readable summary of cleaning operations.

        Returns:
            String summary of what was cleaned
        """
        if self.cleaning_report["columns_cleaned"] == 0:
            return "No cleaning performed (data was already clean)"

        summary = [
            f"Cleaned {self.cleaning_report['columns_cleaned']} columns across {self.cleaning_report['total_rows']} rows",
            "",
            "Transformations applied:"
        ]

        for trans in self.cleaning_report["transformations"]:
            summary.append(
                f"  - {trans['column']}: {', '.join(trans['transformations'])}"
            )

        if self.cleaning_report["errors"]:
            summary.append("")
            summary.append("Errors encountered:")
            for err in self.cleaning_report["errors"]:
                summary.append(f"  - {err['column']}: {err['error']}")

        return "\n".join(summary)


def clean_file(
    file_path: Path,
    column_profiles: Dict[str, List[Dict[str, Any]]]
) -> Tuple[Dict[str, pl.DataFrame], Dict[str, Any]]:
    """
    Clean all sheets in a file based on column profiles.

    Args:
        file_path: Path to the spreadsheet file
        column_profiles: Dict of {sheet_name: [column_profile_dicts]}

    Returns:
        Tuple of (cleaned_sheets_dict, overall_report)
    """
    cleaner = DataCleaner()
    cleaned_sheets = {}
    overall_report = {
        "sheets": {},
        "total_columns_cleaned": 0,
        "total_transformations": 0
    }

    # Read file
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        # Excel - read all sheets
        import pandas as pd
        excel_file = pd.ExcelFile(file_path)
        for sheet_name in excel_file.sheet_names:
            df_pandas = pd.read_excel(excel_file, sheet_name=sheet_name)
            df = pl.from_pandas(df_pandas)

            # Get profiles for this sheet
            profiles_list = column_profiles.get(sheet_name, [])
            profiles_dict = {p["name"]: p for p in profiles_list}

            # Clean
            cleaned_df, report = cleaner.clean_dataframe(df, profiles_dict, sheet_name)
            cleaned_sheets[sheet_name] = cleaned_df
            overall_report["sheets"][sheet_name] = report
            overall_report["total_columns_cleaned"] += report["columns_cleaned"]
            overall_report["total_transformations"] += len(report["transformations"])

    elif file_path.suffix.lower() == '.csv':
        # CSV - single sheet
        df = pl.read_csv(file_path)
        sheet_name = "Sheet1"

        # Get profiles
        profiles_list = column_profiles.get(sheet_name, [])
        profiles_dict = {p["name"]: p for p in profiles_list}

        # Clean
        cleaned_df, report = cleaner.clean_dataframe(df, profiles_dict, sheet_name)
        cleaned_sheets[sheet_name] = cleaned_df
        overall_report["sheets"][sheet_name] = report
        overall_report["total_columns_cleaned"] += report["columns_cleaned"]
        overall_report["total_transformations"] += len(report["transformations"])

    return cleaned_sheets, overall_report
