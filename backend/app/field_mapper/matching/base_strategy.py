"""
Base Strategy for field matching.

This module defines the abstract base class that all matching strategies
must implement.
"""
from abc import ABC, abstractmethod
from typing import List

from ..core.data_structures import FieldMapping, FieldDefinition
from .matching_context import MatchingContext
from ..config.logging_config import matching_logger as logger


class BaseStrategy(ABC):
    """
    Abstract base class for field matching strategies.

    All matching strategies must implement the match() method which takes
    a MatchingContext and returns a list of FieldMapping candidates with
    confidence scores.

    Each strategy focuses on one specific matching technique:
    - Exact name matching
    - Label matching
    - Selection value matching
    - Data type compatibility
    - Pattern matching
    - Statistical similarity
    - Contextual matching
    - Fuzzy string matching
    """

    def __init__(self, weight: float = 1.0):
        """
        Initialize the strategy.

        Args:
            weight: Weight factor for this strategy (0.0 to 1.0)
        """
        self.weight = weight
        self.name = self.__class__.__name__
        logger.debug(f"Initialized strategy: {self.name} (weight={weight})")

    @abstractmethod
    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find matching fields for the given column.

        This is the core method that each strategy must implement.

        Args:
            context: MatchingContext containing all information needed

        Returns:
            List of FieldMapping objects with confidence scores.
            Each FieldMapping should have:
            - target_model: Model name
            - target_field: Field name
            - confidence: Score from 0.0 to 1.0
            - matching_strategy: Name of this strategy
            - rationale: Human-readable explanation
            - scores: Dictionary with detailed scoring breakdown
        """
        pass

    def create_mapping(
        self,
        field: FieldDefinition,
        confidence: float,
        rationale: str,
        scores: dict = None,
        source_column: str = None
    ) -> FieldMapping:
        """
        Helper method to create a FieldMapping object.

        Args:
            field: FieldDefinition that was matched
            confidence: Confidence score (0.0 to 1.0)
            rationale: Human-readable explanation
            scores: Dictionary of detailed scores
            source_column: Source column name (if not from context)

        Returns:
            FieldMapping object
        """
        return FieldMapping(
            source_column=source_column or "",
            target_model=field.model,
            target_field=field.name,
            confidence=confidence * self.weight,  # Apply strategy weight
            scores=scores or {},
            rationale=f"[{self.name}] {rationale}",
            matching_strategy=self.name,
            alternatives=[],
            transformations=[],
        )

    def filter_by_confidence(
        self,
        mappings: List[FieldMapping],
        min_confidence: float = 0.0
    ) -> List[FieldMapping]:
        """
        Filter mappings by minimum confidence threshold.

        Args:
            mappings: List of FieldMapping objects
            min_confidence: Minimum confidence threshold

        Returns:
            Filtered list of FieldMapping objects
        """
        return [m for m in mappings if m.confidence >= min_confidence]

    def sort_by_confidence(
        self,
        mappings: List[FieldMapping],
        descending: bool = True
    ) -> List[FieldMapping]:
        """
        Sort mappings by confidence score.

        Args:
            mappings: List of FieldMapping objects
            descending: If True, sort highest to lowest

        Returns:
            Sorted list of FieldMapping objects
        """
        return sorted(mappings, key=lambda m: m.confidence, reverse=descending)

    def __repr__(self) -> str:
        """String representation of the strategy."""
        return f"{self.name}(weight={self.weight})"
