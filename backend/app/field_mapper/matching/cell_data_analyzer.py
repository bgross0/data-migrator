"""
Cell Data Analyzer for semantic analysis of actual cell values.

This module analyzes the actual values in spreadsheet cells to understand
the semantic meaning of the data, improving field mapping accuracy.
"""
from typing import List, Dict, Any, Optional, Set
from collections import Counter
import re
import statistics
from datetime import datetime
from dataclasses import dataclass

from ..core.data_structures import ColumnProfile
from ..config.logging_config import matching_logger as logger


@dataclass
class ValueAnalysis:
    """Results of cell value analysis."""
    entity_type: Optional[str] = None  # company, person, product, etc.
    value_category: Optional[str] = None  # geographic, financial, temporal, etc.
    reference_type: Optional[str] = None  # invoice, order, product_code, etc.
    field_hints: List[str] = None  # Suggested field names
    confidence: float = 0.0
    metadata: Dict[str, Any] = None


class CellDataAnalyzer:
    """
    Analyzes actual cell values to determine semantic meaning.

    This provides deep understanding of data beyond surface patterns:
    - Entity recognition (companies vs persons)
    - Reference pattern detection
    - Category matching against known Odoo values
    - Statistical distribution analysis
    - Cross-column correlation
    """

    # Common company suffixes
    COMPANY_SUFFIXES = {
        "inc", "corp", "corporation", "llc", "ltd", "limited", "co",
        "company", "group", "holdings", "partners", "associates",
        "gmbh", "sa", "spa", "srl", "ag", "nv", "bv", "plc"
    }

    # Common person name patterns
    PERSON_TITLES = {"mr", "mrs", "ms", "dr", "prof", "sir", "lord", "lady"}

    # Reference patterns
    REFERENCE_PATTERNS = {
        "invoice": [
            r"INV[-/]?\d+",
            r"INVOICE[-/]?\d+",
            r"\d{4}[-/]INV[-/]\d+",
        ],
        "order": [
            r"SO[-/]?\d+",
            r"PO[-/]?\d+",
            r"ORDER[-/]?\d+",
            r"\d{4}[-/]ORD[-/]\d+",
        ],
        "product": [
            r"[A-Z]{2,4}[-]?\d{3,}",  # SKU patterns
            r"PROD[-]?\d+",
            r"\d{5,12}$",  # Barcode/EAN
        ],
        "account": [
            r"\d{3,4}[-.]?\d{3,4}",  # Account numbers
            r"[A-Z]{2}\d{2}[-]?\d{4,}",  # Bank accounts
        ]
    }

    # Geographic indicators
    COUNTRIES = {
        "united states", "usa", "canada", "mexico", "brazil", "argentina",
        "united kingdom", "uk", "france", "germany", "spain", "italy",
        "china", "japan", "india", "australia", "south africa",
        # Add more as needed
    }

    # Common business domains
    INDUSTRIES = {
        "technology", "software", "healthcare", "finance", "retail",
        "manufacturing", "automotive", "energy", "telecommunications",
        "education", "hospitality", "real estate", "construction",
        "transportation", "logistics", "media", "entertainment"
    }

    # Odoo state values
    ODOO_STATES = {
        "draft": ["draft", "new", "pending"],
        "confirmed": ["confirmed", "approved", "validated"],
        "done": ["done", "completed", "finished", "delivered"],
        "cancel": ["cancelled", "canceled", "rejected", "void"]
    }

    def __init__(self):
        """Initialize the cell data analyzer."""
        logger.info("CellDataAnalyzer initialized")
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = {}
        for ref_type, patterns in self.REFERENCE_PATTERNS.items():
            self.compiled_patterns[ref_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def analyze_column(self, column_profile: ColumnProfile) -> ValueAnalysis:
        """
        Perform semantic analysis on a column's values.

        Args:
            column_profile: Profile of the column including sample values

        Returns:
            ValueAnalysis with semantic understanding of the data
        """
        logger.debug(f"Analyzing values for column: {column_profile.column_name}")

        # Get sample values (non-null)
        sample_values = [
            v for v in column_profile.sample_values
            if v is not None and str(v).strip()
        ]

        if not sample_values:
            return ValueAnalysis(confidence=0.0)

        # Run various analyses
        entity_result = self._analyze_entity_type(sample_values)
        reference_result = self._detect_reference_patterns(sample_values)
        category_result = self._categorize_values(sample_values, column_profile)
        geographic_result = self._detect_geographic_data(sample_values)
        state_result = self._detect_state_values(sample_values)

        # Combine results
        analysis = self._combine_analyses(
            entity_result,
            reference_result,
            category_result,
            geographic_result,
            state_result,
            column_profile
        )

        return analysis

    def _analyze_entity_type(self, values: List[Any]) -> Dict[str, Any]:
        """
        Determine if values represent companies, persons, products, etc.

        Args:
            values: List of sample values

        Returns:
            Dict with entity type and confidence
        """
        company_score = 0
        person_score = 0
        product_score = 0

        for value in values[:50]:  # Check first 50 values
            value_str = str(value).strip()
            value_lower = value_str.lower()

            # Check for company indicators
            if any(suffix in value_lower for suffix in self.COMPANY_SUFFIXES):
                company_score += 2
            if any(word in value_lower for word in ["company", "corporation", "group"]):
                company_score += 1

            # Check for person indicators
            words = value_str.split()
            if len(words) == 2 or len(words) == 3:  # Typical person name length
                # Check if first word might be a title
                if words[0].lower() in self.PERSON_TITLES:
                    person_score += 2
                # Check if looks like First Last name
                elif all(word[0].isupper() for word in words if word):
                    person_score += 1

            # Check for product indicators
            if re.match(r'^[A-Z]{2,4}[-]?\d{3,}', value_str):  # SKU pattern
                product_score += 2
            if len(value_str) in [8, 10, 12, 13] and value_str.isdigit():  # Barcode
                product_score += 1

        # Determine entity type
        max_score = max(company_score, person_score, product_score)
        if max_score == 0:
            return {"type": None, "confidence": 0.0}

        if company_score == max_score:
            return {"type": "company", "confidence": min(1.0, company_score / len(values))}
        elif person_score == max_score:
            return {"type": "person", "confidence": min(1.0, person_score / len(values))}
        else:
            return {"type": "product", "confidence": min(1.0, product_score / len(values))}

    def _detect_reference_patterns(self, values: List[Any]) -> Dict[str, Any]:
        """
        Detect reference patterns (invoice numbers, order numbers, etc.).

        Args:
            values: List of sample values

        Returns:
            Dict with reference type and confidence
        """
        pattern_matches = Counter()

        for value in values[:50]:
            value_str = str(value).strip()

            for ref_type, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.match(value_str):
                        pattern_matches[ref_type] += 1
                        break

        if not pattern_matches:
            return {"type": None, "confidence": 0.0}

        # Get most common pattern
        most_common = pattern_matches.most_common(1)[0]
        ref_type, count = most_common
        confidence = min(1.0, count / len(values[:50]))

        return {"type": ref_type, "confidence": confidence}

    def _categorize_values(self, values: List[Any], column_profile: ColumnProfile) -> Dict[str, Any]:
        """
        Categorize values based on their nature.

        Args:
            values: List of sample values
            column_profile: Column profile with additional metadata

        Returns:
            Dict with category and metadata
        """
        # Check if numeric
        if column_profile.data_type in ["integer", "float"]:
            return self._categorize_numeric_values(values)

        # Check if temporal
        if column_profile.data_type == "date":
            return {"category": "temporal", "subtype": "date", "confidence": 0.9}

        # Check if categorical (limited distinct values)
        if column_profile.uniqueness_ratio < 0.1:  # Less than 10% unique
            return self._categorize_categorical_values(values, column_profile)

        # Default to text
        return {"category": "text", "confidence": 0.5}

    def _categorize_numeric_values(self, values: List[Any]) -> Dict[str, Any]:
        """
        Categorize numeric values based on their range and distribution.

        Args:
            values: List of numeric values

        Returns:
            Dict with numeric category
        """
        numeric_values = []
        for v in values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                continue

        if not numeric_values:
            return {"category": "numeric", "confidence": 0.5}

        min_val = min(numeric_values)
        max_val = max(numeric_values)
        mean_val = statistics.mean(numeric_values)

        # Detect currency amounts
        if min_val >= 0 and max_val < 1000000 and any(v % 0.01 == 0 for v in numeric_values[:20]):
            return {
                "category": "financial",
                "subtype": "currency",
                "confidence": 0.8,
                "range": [min_val, max_val]
            }

        # Detect quantities
        if all(v == int(v) for v in numeric_values) and min_val >= 0 and max_val < 10000:
            return {
                "category": "quantity",
                "subtype": "integer",
                "confidence": 0.7,
                "range": [min_val, max_val]
            }

        # Detect percentages
        if 0 <= min_val <= 100 and 0 <= max_val <= 100:
            return {
                "category": "percentage",
                "confidence": 0.6,
                "range": [min_val, max_val]
            }

        return {
            "category": "numeric",
            "confidence": 0.5,
            "range": [min_val, max_val],
            "mean": mean_val
        }

    def _categorize_categorical_values(self, values: List[Any], column_profile: ColumnProfile) -> Dict[str, Any]:
        """
        Analyze categorical values.

        Args:
            values: List of values
            column_profile: Column profile

        Returns:
            Dict with category analysis
        """
        # Get unique values
        unique_values = set(str(v).lower() for v in values if v is not None)

        # Check against known categories
        if self._matches_state_values(unique_values):
            return {
                "category": "selection",
                "subtype": "state",
                "confidence": 0.8,
                "values": list(unique_values)[:10]
            }

        if self._matches_boolean_values(unique_values):
            return {
                "category": "boolean",
                "confidence": 0.9,
                "values": list(unique_values)
            }

        return {
            "category": "categorical",
            "confidence": 0.6,
            "distinct_count": len(unique_values),
            "values": list(unique_values)[:10]
        }

    def _detect_geographic_data(self, values: List[Any]) -> Dict[str, Any]:
        """
        Detect geographic data (countries, cities, regions).

        Args:
            values: List of sample values

        Returns:
            Dict with geographic type
        """
        country_matches = 0
        city_indicators = 0

        for value in values[:50]:
            value_lower = str(value).lower().strip()

            # Check for country names
            if value_lower in self.COUNTRIES:
                country_matches += 1

            # Check for city indicators (capitalized words)
            words = str(value).split()
            if 1 <= len(words) <= 3 and all(w[0].isupper() for w in words if w):
                city_indicators += 1

        if country_matches > len(values) * 0.3:
            return {"type": "country", "confidence": 0.8}

        if city_indicators > len(values) * 0.5:
            return {"type": "city_or_region", "confidence": 0.6}

        return {"type": None, "confidence": 0.0}

    def _detect_state_values(self, values: List[Any]) -> Dict[str, Any]:
        """
        Detect if values match Odoo state patterns.

        Args:
            values: List of sample values

        Returns:
            Dict with state detection results
        """
        value_set = set(str(v).lower() for v in values if v)

        for state_type, state_values in self.ODOO_STATES.items():
            if any(sv in value_set for sv in state_values):
                return {
                    "type": "state",
                    "state_type": state_type,
                    "confidence": 0.7
                }

        return {"type": None, "confidence": 0.0}

    def _matches_state_values(self, unique_values: Set[str]) -> bool:
        """Check if values match known state values."""
        for state_values in self.ODOO_STATES.values():
            if any(sv in unique_values for sv in state_values):
                return True
        return False

    def _matches_boolean_values(self, unique_values: Set[str]) -> bool:
        """Check if values are boolean-like."""
        boolean_sets = [
            {"yes", "no"},
            {"true", "false"},
            {"1", "0"},
            {"y", "n"},
            {"active", "inactive"},
            {"enabled", "disabled"}
        ]

        for bool_set in boolean_sets:
            if unique_values <= bool_set:
                return True
        return False

    def _combine_analyses(
        self,
        entity_result: Dict,
        reference_result: Dict,
        category_result: Dict,
        geographic_result: Dict,
        state_result: Dict,
        column_profile: ColumnProfile
    ) -> ValueAnalysis:
        """
        Combine all analysis results into final ValueAnalysis.

        Args:
            Various analysis results and column profile

        Returns:
            Combined ValueAnalysis
        """
        analysis = ValueAnalysis()

        # Set entity type
        if entity_result.get("confidence", 0) > 0.5:
            analysis.entity_type = entity_result["type"]

        # Set reference type
        if reference_result.get("confidence", 0) > 0.5:
            analysis.reference_type = reference_result["type"]

        # Set value category
        analysis.value_category = category_result.get("category")

        # Generate field hints based on all analyses
        field_hints = []

        # Entity-based hints
        if analysis.entity_type == "company":
            field_hints.extend(["res.partner.name", "res.partner.company_name"])
        elif analysis.entity_type == "person":
            field_hints.extend(["res.partner.name", "hr.employee.name"])
        elif analysis.entity_type == "product":
            field_hints.extend(["product.product.name", "product.product.default_code"])

        # Reference-based hints
        if analysis.reference_type == "invoice":
            field_hints.extend(["account.move.name", "account.move.ref"])
        elif analysis.reference_type == "order":
            field_hints.extend(["sale.order.name", "purchase.order.name"])

        # Category-based hints
        if category_result.get("subtype") == "currency":
            field_hints.extend(["amount", "price", "cost", "total"])
        elif category_result.get("subtype") == "state":
            field_hints.extend(["state", "status"])

        # Geographic hints
        if geographic_result.get("type") == "country":
            field_hints.extend(["res.partner.country_id", "res.country"])
        elif geographic_result.get("type") == "city_or_region":
            field_hints.extend(["res.partner.city", "res.partner.state_id"])

        analysis.field_hints = field_hints

        # Calculate overall confidence
        confidences = [
            entity_result.get("confidence", 0),
            reference_result.get("confidence", 0),
            category_result.get("confidence", 0),
            geographic_result.get("confidence", 0),
            state_result.get("confidence", 0)
        ]
        analysis.confidence = max(confidences) if confidences else 0.0

        # Store metadata
        analysis.metadata = {
            "column_name": column_profile.column_name,
            "data_type": column_profile.data_type,
            "sample_size": len(column_profile.sample_values),
            "uniqueness_ratio": column_profile.uniqueness_ratio
        }

        logger.debug(f"Analysis complete for '{column_profile.column_name}': {analysis.entity_type or analysis.value_category}")

        return analysis

    def suggest_field_mappings(
        self,
        column_profile: ColumnProfile,
        available_models: Set[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest specific field mappings based on value analysis.

        Args:
            column_profile: Column profile with values
            available_models: Set of models to consider (from module selection)

        Returns:
            List of suggested field mappings with confidence
        """
        analysis = self.analyze_column(column_profile)

        suggestions = []

        # Generate suggestions based on analysis
        if analysis.field_hints:
            for hint in analysis.field_hints:
                # Parse model.field format
                if "." in hint:
                    model, field = hint.rsplit(".", 1)
                    # Check if model is in available set
                    if available_models and model not in available_models:
                        continue
                    suggestions.append({
                        "model": model,
                        "field": field,
                        "confidence": analysis.confidence,
                        "reason": f"Value analysis: {analysis.entity_type or analysis.value_category}"
                    })

        return suggestions[:5]  # Return top 5 suggestions