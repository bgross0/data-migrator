"""
Matching strategies for field mapping.

This module contains all the matching strategies used by the field mapper.
"""
from .exact_name_match import ExactNameMatchStrategy
from .label_match import LabelMatchStrategy
from .selection_value_match import SelectionValueMatchStrategy
from .data_type_compatibility import DataTypeCompatibilityStrategy
from .pattern_match import PatternMatchStrategy
from .statistical_similarity import StatisticalSimilarityStrategy
from .contextual_match import ContextualMatchStrategy
from .fuzzy_match import FuzzyMatchStrategy

__all__ = [
    "ExactNameMatchStrategy",
    "LabelMatchStrategy",
    "SelectionValueMatchStrategy",
    "DataTypeCompatibilityStrategy",
    "PatternMatchStrategy",
    "StatisticalSimilarityStrategy",
    "ContextualMatchStrategy",
    "FuzzyMatchStrategy",
]
