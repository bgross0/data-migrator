"""
Header matching system - maps spreadsheet column names to Odoo model fields.
Uses exact, fuzzy, and AI-powered matching strategies.
"""
from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz, process
import re
from app.core.odoo_synonyms import get_all_fields_for_model, get_model_from_sheet_name


class HeaderMatcher:
    """Matches spreadsheet column headers to Odoo model fields."""

    def __init__(self, target_model: str = "res.partner"):
        """
        Initialize matcher for a specific Odoo model.

        Args:
            target_model: Target Odoo model (e.g., "res.partner")
        """
        self.target_model = target_model
        self.field_synonyms = get_all_fields_for_model(target_model)

    def match(self, header: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate ranked mapping suggestions for a header.

        Args:
            header: Column header name
            sheet_name: Optional sheet name for model detection

        Returns:
            List of candidates: [{model, field, confidence, method, rationale}]
        """
        # Auto-detect model from sheet name if provided
        if sheet_name:
            detected_model = get_model_from_sheet_name(sheet_name)
            if detected_model != self.target_model:
                self.target_model = detected_model
                self.field_synonyms = get_all_fields_for_model(detected_model)

        candidates = []
        normalized_header = self._normalize(header)

        # 1. Exact match
        exact = self._exact_match(normalized_header)
        if exact:
            candidates.extend(exact)

        # 2. Synonym match
        synonym = self._synonym_match(normalized_header)
        if synonym:
            candidates.extend(synonym)

        # 3. Fuzzy match
        fuzzy = self._fuzzy_match(normalized_header, threshold=70)
        candidates.extend(fuzzy)

        # Deduplicate and sort by confidence
        candidates = self._deduplicate(candidates)
        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        return candidates[:5]  # Top 5

    def _normalize(self, text: str) -> str:
        """Normalize text for matching: lowercase, remove punctuation, trim."""
        text = text.lower().strip()
        # Remove common punctuation but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _exact_match(self, normalized_header: str) -> List[Dict[str, Any]]:
        """Find exact matches in field names."""
        matches = []

        for field_name, synonyms in self.field_synonyms.items():
            # Check if header exactly matches field name
            if normalized_header == field_name.replace('_', ' '):
                matches.append({
                    "model": self.target_model,
                    "field": field_name,
                    "confidence": 1.0,
                    "method": "exact_field",
                    "rationale": f"Exact match to field name '{field_name}'"
                })

        return matches

    def _synonym_match(self, normalized_header: str) -> List[Dict[str, Any]]:
        """Find matches using synonym dictionary."""
        matches = []

        for field_name, synonyms in self.field_synonyms.items():
            for synonym in synonyms:
                if normalized_header == synonym:
                    matches.append({
                        "model": self.target_model,
                        "field": field_name,
                        "confidence": 0.95,
                        "method": "synonym",
                        "rationale": f"Synonym match: '{normalized_header}' → '{field_name}'"
                    })
                    break  # Only one match per field

        return matches

    def _fuzzy_match(self, normalized_header: str, threshold: int = 70) -> List[Dict[str, Any]]:
        """Find fuzzy matches using rapidfuzz."""
        matches = []

        # Build list of all possible match targets
        targets = []
        for field_name, synonyms in self.field_synonyms.items():
            targets.append((field_name.replace('_', ' '), field_name))
            for synonym in synonyms:
                targets.append((synonym, field_name))

        # Use rapidfuzz to find best matches
        target_strings = [t[0] for t in targets]
        results = process.extract(
            normalized_header,
            target_strings,
            scorer=fuzz.token_sort_ratio,
            limit=10
        )

        # Convert results to candidates
        seen_fields = set()
        for match_text, score, _ in results:
            if score < threshold:
                continue

            # Find which field this match corresponds to
            field_name = None
            for target_text, target_field in targets:
                if target_text == match_text:
                    field_name = target_field
                    break

            if field_name and field_name not in seen_fields:
                seen_fields.add(field_name)

                # Determine confidence based on score
                confidence = score / 100.0

                # Adjust confidence based on score ranges
                if score >= 90:
                    confidence = 0.90
                elif score >= 75:
                    confidence = 0.75
                else:
                    confidence = 0.60

                matches.append({
                    "model": self.target_model,
                    "field": field_name,
                    "confidence": confidence,
                    "method": "fuzzy",
                    "rationale": f"Fuzzy match (score: {score}): '{normalized_header}' → '{match_text}'"
                })

        return matches

    def _deduplicate(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate candidates, keeping highest confidence."""
        seen = {}
        for candidate in candidates:
            key = (candidate["model"], candidate["field"])
            if key not in seen or candidate["confidence"] > seen[key]["confidence"]:
                seen[key] = candidate

        return list(seen.values())
