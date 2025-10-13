"""
Fuzzy Match Strategy.

This strategy matches columns to fields using fuzzy string matching.
"""
from typing import List
import difflib

from ..base_strategy import BaseStrategy
from ..matching_context import MatchingContext
from ...core.data_structures import FieldMapping
from ...config.logging_config import matching_logger as logger


class FuzzyMatchStrategy(BaseStrategy):
    """
    Matches columns to fields using fuzzy string matching.

    This strategy is a fallback for when exact matches don't work. It uses
    string similarity algorithms to find fields with similar names.

    Examples:
    - "cust_name" -> "customer_name" (similarity ~0.73)
    - "addr" -> "address" (similarity ~0.62)
    - "qty" -> "quantity" (similarity ~0.55)
    """

    def __init__(self, weight: float = 0.65):
        """
        Initialize the fuzzy match strategy.

        Args:
            weight: Strategy weight (default 0.65)
        """
        super().__init__(weight=weight)
        self.min_similarity = 0.6  # Minimum similarity threshold

    def match(self, context: MatchingContext) -> List[FieldMapping]:
        """
        Find fields with similar names using fuzzy matching.

        Args:
            context: MatchingContext with column profile and knowledge base

        Returns:
            List of FieldMapping objects with confidence scores
        """
        column_name = context.column_profile.column_name
        logger.debug(f"FuzzyMatch: Searching for fuzzy matches for '{column_name}'")

        # Normalize column name
        normalized_col = self._normalize_name(column_name)

        # Get all candidate fields
        candidate_fields = context.get_candidate_fields()

        if not candidate_fields:
            logger.debug("FuzzyMatch: No candidate fields to search")
            return []

        logger.debug(f"FuzzyMatch: Searching through {len(candidate_fields)} candidate fields")

        mappings = []

        # Calculate similarity for each candidate field
        for field in candidate_fields:
            # Try matching against field name
            field_name_similarity = self._calculate_similarity(
                normalized_col,
                self._normalize_name(field.name)
            )

            # Try matching against field label
            field_label_similarity = self._calculate_similarity(
                normalized_col,
                self._normalize_name(field.label)
            )

            # Take the best similarity
            best_similarity = max(field_name_similarity, field_label_similarity)

            if best_similarity < self.min_similarity:
                continue

            # Determine which match was better
            if field_name_similarity > field_label_similarity:
                match_type = "field name"
                match_value = field.name
            else:
                match_type = "field label"
                match_value = field.label

            # Calculate confidence
            confidence = best_similarity * 0.85  # Moderate confidence for fuzzy matches

            rationale = (
                f"Fuzzy match: column name '{column_name}' is similar to "
                f"{match_type} '{match_value}' (similarity={best_similarity:.2f})"
            )

            scores = {
                "fuzzy_similarity": best_similarity,
                "field_name_similarity": field_name_similarity,
                "field_label_similarity": field_label_similarity,
                "match_type": match_type,
            }

            mapping = self.create_mapping(
                field=field,
                confidence=confidence,
                rationale=rationale,
                scores=scores,
                source_column=column_name,
            )

            mappings.append(mapping)

        logger.info(
            f"FuzzyMatch: Found {len(mappings)} fuzzy matches "
            f"(min_similarity={self.min_similarity})"
        )

        # Return top 10 matches only (to avoid too many low-confidence matches)
        sorted_mappings = self.sort_by_confidence(mappings)
        return sorted_mappings[:10]

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a name for comparison.

        Args:
            name: Name to normalize

        Returns:
            Normalized name (lowercase, no special chars)
        """
        import re

        # Remove special characters, keep only alphanumeric and spaces
        normalized = re.sub(r"[^a-z0-9\s]", " ", name.lower())

        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using multiple algorithms.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score from 0.0 to 1.0
        """
        if not str1 or not str2:
            return 0.0

        # Use SequenceMatcher for character-level similarity
        sequence_sim = difflib.SequenceMatcher(None, str1, str2).ratio()

        # Token-based similarity (Jaccard)
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())

        if tokens1 and tokens2:
            intersection = tokens1 & tokens2
            union = tokens1 | tokens2
            token_sim = len(intersection) / len(union)
        else:
            token_sim = 0.0

        # Substring similarity (one contains the other)
        if str1 in str2 or str2 in str1:
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            substring_sim = shorter / longer
        else:
            substring_sim = 0.0

        # Combine similarities (weighted average)
        combined_similarity = (
            sequence_sim * 0.5 +
            token_sim * 0.3 +
            substring_sim * 0.2
        )

        return combined_similarity

    def get_close_matches(
        self,
        word: str,
        possibilities: List[str],
        n: int = 10,
        cutoff: float = 0.6
    ) -> List[tuple]:
        """
        Get close matches to a word from a list of possibilities.

        Args:
            word: Word to match
            possibilities: List of possible matches
            n: Maximum number of matches to return
            cutoff: Minimum similarity threshold

        Returns:
            List of (match, similarity) tuples
        """
        normalized_word = self._normalize_name(word)

        matches = []
        for possibility in possibilities:
            normalized_possibility = self._normalize_name(possibility)
            similarity = self._calculate_similarity(normalized_word, normalized_possibility)

            if similarity >= cutoff:
                matches.append((possibility, similarity))

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:n]
