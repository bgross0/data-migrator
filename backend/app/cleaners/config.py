"""
Configuration for data cleaning operations.

Defines what cleaning rules to run and their settings.
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CleaningConfig:
    """
    Configuration for data cleaning.

    Controls which rules are enabled and their specific settings.
    """

    # ==================== Rule Enablement ====================

    # Header detection
    detect_headers: bool = True

    # Column name cleaning
    clean_column_names: bool = True

    # Data value cleaning
    trim_whitespace: bool = True
    decode_html_entities: bool = True
    clean_currency: bool = True

    # Column management
    drop_empty_columns: bool = True
    handle_duplicate_columns: bool = True

    # ==================== Rule-Specific Settings ====================

    # HeaderDetectionRule settings
    header_detection_method: str = "auto"  # "auto", "row_0", "row_1", or integer
    max_rows_to_check: int = 10  # How many rows to check for headers

    # ColumnNameCleaningRule settings
    remove_parentheses: bool = True  # Remove " (Contact)" etc
    remove_special_chars: bool = True  # Remove *, ?, #, etc
    special_chars_to_remove: str = "*?#"  # Which special chars to strip
    normalize_spaces: bool = True  # Multiple spaces → single space

    # WhitespaceRule settings
    trim_column_names: bool = True  # Also trim column names
    normalize_internal_spaces: bool = False  # "a  b" → "a b"

    # HTMLEntityRule settings
    decode_all_entities: bool = True  # Decode all vs just common ones

    # CurrencyRule settings
    auto_detect_currency: bool = True  # Auto-detect currency columns
    currency_symbols: List[str] = None  # Defaults to ["$", "€", "£", "¥"]

    # EmptyColumnRule settings
    empty_threshold: float = 0.95  # Drop if >95% null
    always_drop_all_null: bool = True  # Always drop 100% null columns

    # DuplicateColumnRule settings
    duplicate_strategy: str = "rename"  # "rename", "drop", "merge"

    # ==================== Output Settings ====================

    preserve_original_names: bool = True  # Keep original column names in report
    verbose: bool = False  # Detailed logging

    def __post_init__(self):
        """Set defaults for mutable fields."""
        if self.currency_symbols is None:
            self.currency_symbols = ["$", "€", "£", "¥"]

    @classmethod
    def default(cls) -> "CleaningConfig":
        """Create config with default settings (all rules enabled)."""
        return cls()

    @classmethod
    def conservative(cls) -> "CleaningConfig":
        """
        Create conservative config (only essential rules).

        Good for testing or when you don't want aggressive cleaning.
        """
        return cls(
            detect_headers=True,
            clean_column_names=True,
            trim_whitespace=True,
            decode_html_entities=True,
            clean_currency=False,  # Disabled
            drop_empty_columns=False,  # Disabled
            handle_duplicate_columns=True,
        )

    @classmethod
    def aggressive(cls) -> "CleaningConfig":
        """
        Create aggressive config (all rules, lower thresholds).

        Good for very messy data.
        """
        return cls(
            detect_headers=True,
            clean_column_names=True,
            trim_whitespace=True,
            decode_html_entities=True,
            clean_currency=True,
            drop_empty_columns=True,
            handle_duplicate_columns=True,
            empty_threshold=0.80,  # Drop if >80% null (more aggressive)
            normalize_internal_spaces=True,  # Clean internal spaces too
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "detect_headers": self.detect_headers,
            "clean_column_names": self.clean_column_names,
            "trim_whitespace": self.trim_whitespace,
            "decode_html_entities": self.decode_html_entities,
            "clean_currency": self.clean_currency,
            "drop_empty_columns": self.drop_empty_columns,
            "handle_duplicate_columns": self.handle_duplicate_columns,
            "settings": {
                "header_detection_method": self.header_detection_method,
                "empty_threshold": self.empty_threshold,
                "duplicate_strategy": self.duplicate_strategy,
            }
        }
