"""
Data cleaning module for spreadsheet imports.

Provides tools to clean messy real-world data before profiling and matching.
"""
from .data_cleaner import DataCleaner
from .config import CleaningConfig
from .report import CleaningReport
from .base import CleaningRule, CleaningResult, Change, ChangeType

__all__ = [
    "DataCleaner",
    "CleaningConfig",
    "CleaningReport",
    "CleaningRule",
    "CleaningResult",
    "Change",
    "ChangeType",
]
