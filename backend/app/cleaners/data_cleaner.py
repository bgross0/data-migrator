"""
Main data cleaning orchestrator using Polars.

Runs cleaning rules in priority order and generates a comprehensive report.
"""
from pathlib import Path
from typing import List, Tuple, Optional, Union
import polars as pl
import logging

from .base import CleaningRule, CleaningResult
from .config import CleaningConfig
from .report import CleaningReport


logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Orchestrates data cleaning operations.

    Runs multiple cleaning rules in priority order and tracks all changes.
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        """
        Initialize the data cleaner.

        Args:
            config: Cleaning configuration. If None, uses default config.
        """
        self.config = config or CleaningConfig.default()
        self.rules: List[CleaningRule] = []

    def register_rule(self, rule: CleaningRule):
        """
        Register a cleaning rule.

        Args:
            rule: Cleaning rule to register
        """
        self.rules.append(rule)
        # Sort rules by priority (lower = earlier)
        self.rules.sort(key=lambda r: r.priority)

    def register_rules(self, rules: List[CleaningRule]):
        """
        Register multiple cleaning rules.

        Args:
            rules: List of rules to register
        """
        for rule in rules:
            self.register_rule(rule)

    def clean(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, CleaningReport]:
        """
        Clean a Polars DataFrame using registered rules.

        Args:
            df: Input Polars DataFrame to clean

        Returns:
            Tuple of (cleaned DataFrame, cleaning report)
        """
        # Initialize report
        report = CleaningReport(
            original_shape=(df.height, df.width),
            config_used=self.config.to_dict()
        )

        # Store original column names for mapping
        original_columns = df.columns

        # Clone to avoid modifying original
        df_cleaned = df.clone()

        logger.info(f"Starting data cleaning with {len(self.rules)} rules")

        # Run each rule in priority order
        for rule in self.rules:
            logger.info(f"Running rule: {rule.name} (priority={rule.priority})")

            try:
                # Run the rule
                result: CleaningResult = rule.clean(df_cleaned)

                # Update DataFrame
                df_cleaned = result.df

                # Track changes
                for change in result.changes:
                    report.add_change(change.to_dict())

                # Track warnings
                for warning in result.warnings:
                    report.add_warning(f"[{rule.name}] {warning}")

                # Track statistics
                if result.stats:
                    report.add_rule_stats(rule.name, result.stats)

                logger.info(f"Rule '{rule.name}' completed: {len(result.changes)} changes, {len(result.warnings)} warnings")

            except Exception as e:
                error_msg = f"Rule '{rule.name}' failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                report.add_warning(error_msg)
                # Continue with other rules

        # Build column name mapping
        # (This is approximate since columns may have been added/removed)
        final_columns = df_cleaned.columns

        # Try to match original to final columns
        for orig_col in original_columns:
            if orig_col in final_columns:
                # Column still exists (unchanged or renamed back)
                report.column_mappings[orig_col] = orig_col
            elif orig_col not in final_columns:
                # Column was either renamed or dropped
                # For now, just mark as dropped
                if orig_col not in report.columns_dropped:
                    report.columns_dropped.append(orig_col)

        # Add any new columns that appeared
        for final_col in final_columns:
            if final_col not in report.column_mappings.values():
                # This is a renamed column or new column
                # Try to find the original name from changes
                found = False
                for change in report.changes:
                    if (change.get("type") == "column_renamed" and
                        change.get("details", {}).get("new_name") == final_col):
                        old_name = change["details"].get("old_name")
                        if old_name:
                            report.column_mappings[old_name] = final_col
                            found = True
                            break

                if not found:
                    # Assume it's unchanged
                    report.column_mappings[final_col] = final_col

        # Update final shape
        report.cleaned_shape = (df_cleaned.height, df_cleaned.width)

        logger.info(f"Cleaning completed: {report.original_shape} → {report.cleaned_shape}")

        return df_cleaned, report

    def clean_file(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = 0
    ) -> Tuple[pl.DataFrame, CleaningReport]:
        """
        Clean a file (Excel or CSV) using Polars.

        Args:
            file_path: Path to the file
            sheet_name: Sheet name or index for Excel files

        Returns:
            Tuple of (cleaned DataFrame, cleaning report)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Loading file: {file_path}")

        # Load the file
        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            # Excel file - don't use header parameter yet (HeaderDetectionRule will handle it)
            df = pl.read_excel(file_path, sheet_id=sheet_name, has_header=False)
        elif file_path.suffix.lower() == '.csv':
            df = pl.read_csv(file_path, has_header=False)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        logger.info(f"Loaded {df.height} rows × {df.width} columns")

        # Clean the DataFrame
        return self.clean(df)

    def clean_with_default_rules(
        self,
        df: pl.DataFrame
    ) -> Tuple[pl.DataFrame, CleaningReport]:
        """
        Clean a DataFrame using default rules based on config.

        This is a convenience method that automatically registers
        appropriate rules based on the config.

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (cleaned DataFrame, cleaning report)
        """
        # Import rules here to avoid circular imports
        from .rules.header_detection import HeaderDetectionRule
        from .rules.column_name import ColumnNameCleaningRule
        from .rules.whitespace import WhitespaceRule
        from .rules.html_entity import HTMLEntityRule

        # Register rules based on config
        if self.config.detect_headers:
            self.register_rule(HeaderDetectionRule(self.config))

        if self.config.clean_column_names:
            self.register_rule(ColumnNameCleaningRule(self.config))

        if self.config.trim_whitespace:
            self.register_rule(WhitespaceRule(self.config))

        if self.config.decode_html_entities:
            self.register_rule(HTMLEntityRule(self.config))

        # Run cleaning
        return self.clean(df)

    def __repr__(self) -> str:
        return f"<DataCleaner: {len(self.rules)} rules registered>"
