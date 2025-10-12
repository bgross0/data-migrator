"""
Base classes and interfaces for data cleaning.

This module provides the abstract base class for all cleaning rules,
as well as data structures for tracking cleaning results and changes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import pandas as pd


class ChangeType(Enum):
    """Types of changes that can be made during cleaning."""
    HEADER_DETECTION = "header_detection"
    COLUMN_RENAMED = "column_renamed"
    COLUMN_DROPPED = "column_dropped"
    VALUE_MODIFIED = "value_modified"
    ROW_DROPPED = "row_dropped"
    DTYPE_CHANGED = "dtype_changed"


@dataclass
class Change:
    """Represents a single change made during cleaning."""
    change_type: ChangeType
    description: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "type": self.change_type.value,
            "description": self.description,
            "details": self.details
        }


@dataclass
class CleaningResult:
    """
    Result of a cleaning rule execution.

    Contains the cleaned DataFrame plus metadata about what changed.
    """
    df: pd.DataFrame
    changes: List[Change] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def add_change(self, change_type: ChangeType, description: str, details: Optional[Dict[str, Any]] = None):
        """Convenience method to add a change."""
        self.changes.append(Change(
            change_type=change_type,
            description=description,
            details=details or {}
        ))

    def add_warning(self, message: str):
        """Convenience method to add a warning."""
        self.warnings.append(message)

    def to_dict(self) -> dict:
        """Convert to dictionary (excludes DataFrame)."""
        return {
            "changes": [c.to_dict() for c in self.changes],
            "warnings": self.warnings,
            "stats": self.stats
        }


class CleaningRule(ABC):
    """
    Abstract base class for all cleaning rules.

    Each rule performs a specific data cleaning operation and returns
    a CleaningResult with the modified DataFrame and change log.
    """

    @abstractmethod
    def clean(self, df: pd.DataFrame) -> CleaningResult:
        """
        Clean the dataframe according to this rule's logic.

        Args:
            df: Input DataFrame to clean

        Returns:
            CleaningResult with cleaned DataFrame and metadata
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this rule."""
        pass

    @property
    def priority(self) -> int:
        """
        Execution priority (lower number = runs earlier).

        Default is 50. Override to control execution order.
        Critical rules like header detection should be < 20.
        """
        return 50

    @property
    def description(self) -> str:
        """Description of what this rule does."""
        return ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name} (priority={self.priority})>"


class CleaningRuleError(Exception):
    """Raised when a cleaning rule encounters an error."""
    pass


def safe_rule_execution(func):
    """
    Decorator for safe rule execution.

    Catches exceptions and converts them to warnings in the result.
    """
    def wrapper(self, df: pd.DataFrame) -> CleaningResult:
        try:
            return func(self, df)
        except Exception as e:
            # Return original df with error logged
            result = CleaningResult(df=df.copy())
            result.add_warning(f"Rule '{self.name}' failed: {str(e)}")
            result.stats["error"] = str(e)
            return result
    return wrapper
