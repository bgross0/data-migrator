"""
Business Context Analyzer for intelligent model detection.

This module analyzes column combinations, data patterns, and statistical properties
to identify the business domain and appropriate Odoo models.
"""
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
from dataclasses import dataclass
import re

from ..core.data_structures import ColumnProfile
from ..config.logging_config import matching_logger as logger


@dataclass
class DomainSignature:
    """Represents a business domain signature."""
    name: str
    required_columns: Set[str]  # Must have most of these
    optional_columns: Set[str]  # Nice to have
    models: List[str]  # Relevant Odoo models for this domain
    confidence_threshold: float = 0.6


class BusinessContextAnalyzer:
    """
    Analyzes business context from column profiles to detect appropriate models.

    This replaces the naive voting system with intelligent domain detection based on:
    - Column combination patterns
    - Data value analysis
    - Statistical properties
    - Semantic relationships
    """

    # Define business domain signatures
    DOMAIN_SIGNATURES = [
        DomainSignature(
            name="sales_revenue",
            required_columns={
                "product", "item", "sku", "description",
                "quantity", "qty", "units", "amount", "volume",
                "price", "unit_price", "cost", "rate",
                "total", "subtotal", "amount", "revenue", "sales"
            },
            optional_columns={
                "discount", "tax", "customer", "date", "order",
                "segment", "category", "region", "country"
            },
            models=[
                "sale.order.line",
                "account.analytic.line",
                "sale.order",
                "product.product"
            ]
        ),
        DomainSignature(
            name="financial_analysis",
            required_columns={
                "amount", "value", "total", "revenue", "sales", "profit",
                "segment", "account", "analytic", "cost_center",
                "date", "period", "month", "quarter", "year"
            },
            optional_columns={
                "budget", "actual", "variance", "margin", "percentage",
                "region", "country", "department", "project"
            },
            models=[
                "account.analytic.line",
                "account.analytic.account",
                "account.move.line",
                "account.move"
            ]
        ),
        DomainSignature(
            name="inventory",
            required_columns={
                "product", "item", "sku", "code",
                "quantity", "qty", "stock", "on_hand",
                "location", "warehouse", "bin"
            },
            optional_columns={
                "cost", "value", "category", "uom", "unit",
                "minimum", "maximum", "reorder"
            },
            models=[
                "product.product",
                "stock.quant",
                "stock.move",
                "stock.picking"
            ]
        ),
        DomainSignature(
            name="customer_contacts",
            required_columns={
                "name", "company", "customer", "client",
                "email", "phone", "mobile", "contact"
            },
            optional_columns={
                "address", "street", "city", "state", "country", "country_id", "zip",
                "website", "fax", "notes", "type", "category"
            },
            models=[
                "res.partner"  # Primary model for contacts - removed crm.lead to be more focused
            ],
            confidence_threshold=0.4  # Lower threshold for customer data
        ),
        DomainSignature(
            name="hr_timesheet",
            required_columns={
                "employee", "worker", "staff", "name",
                "hours", "time", "duration",
                "date", "day", "week"
            },
            optional_columns={
                "project", "task", "activity", "description",
                "rate", "cost", "department", "overtime"
            },
            models=[
                "account.analytic.line",
                "hr.employee",
                "project.task"
            ]
        ),
        DomainSignature(
            name="purchase_orders",
            required_columns={
                "vendor", "supplier",
                "product", "item",
                "quantity", "qty",
                "price", "cost", "amount"
            },
            optional_columns={
                "po", "purchase_order", "date", "delivery",
                "terms", "status", "approved"
            },
            models=[
                "purchase.order",
                "purchase.order.line",
                "account.move"
            ]
        ),
        DomainSignature(
            name="invoices",
            required_columns={
                "invoice", "bill", "number",
                "amount", "total",
                "date", "due_date",
                "customer", "vendor", "partner"
            },
            optional_columns={
                "tax", "subtotal", "paid", "balance",
                "terms", "reference", "status"
            },
            models=[
                "account.move",
                "account.move.line",
                "account.payment"
            ]
        )
    ]

    def __init__(self):
        """Initialize the business context analyzer."""
        logger.info("BusinessContextAnalyzer initialized")

    def analyze_context(
        self,
        column_profiles: List[ColumnProfile],
        top_n: int = 5
    ) -> Dict[str, float]:
        """
        Analyze column profiles to detect business context and suggest models.

        Args:
            column_profiles: List of column profiles from the spreadsheet
            top_n: Number of top models to return

        Returns:
            Dictionary of model names with confidence scores
        """
        logger.info(f"Analyzing business context for {len(column_profiles)} columns")

        # Extract column names and normalize
        column_names = [self._normalize_column_name(p.column_name) for p in column_profiles]
        column_name_set = set(column_names)

        # Detect matching domains
        domain_scores = self._score_domains(column_name_set, column_profiles)

        # Get models from top matching domains
        model_scores = self._aggregate_model_scores(domain_scores)

        # Filter and sort models
        top_models = dict(sorted(
            model_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n])

        logger.info(f"Top models detected: {list(top_models.keys())}")

        return top_models

    def _normalize_column_name(self, name: str) -> str:
        """
        Normalize column name for matching.

        Args:
            name: Original column name

        Returns:
            Normalized name (lowercase, underscores for spaces)
        """
        # Remove special characters and normalize
        normalized = re.sub(r'[^a-z0-9\s_-]', '', name.lower())
        normalized = re.sub(r'[\s-]+', '_', normalized)
        return normalized.strip('_')

    def _score_domains(
        self,
        column_names: Set[str],
        column_profiles: List[ColumnProfile]
    ) -> List[Tuple[DomainSignature, float]]:
        """
        Score each domain signature against the column set.

        Args:
            column_names: Set of normalized column names
            column_profiles: List of column profiles with data patterns

        Returns:
            List of (DomainSignature, score) tuples
        """
        domain_scores = []

        for domain in self.DOMAIN_SIGNATURES:
            score = self._calculate_domain_score(
                domain, column_names, column_profiles
            )
            if score >= domain.confidence_threshold:
                domain_scores.append((domain, score))
                logger.debug(f"Domain '{domain.name}' scored {score:.2f}")

        return domain_scores

    def _calculate_domain_score(
        self,
        domain: DomainSignature,
        column_names: Set[str],
        column_profiles: List[ColumnProfile]
    ) -> float:
        """
        Calculate matching score for a domain signature.

        Args:
            domain: Domain signature to test
            column_names: Set of column names
            column_profiles: Column profiles with patterns

        Returns:
            Score between 0.0 and 1.0
        """
        # Check required columns (fuzzy match)
        required_matches = 0
        for required_col in domain.required_columns:
            if self._fuzzy_column_match(required_col, column_names):
                required_matches += 1

        # Special case for customer_contacts: having name + (email or phone) is enough
        if domain.name == "customer_contacts":
            has_name = self._fuzzy_column_match("name", column_names)
            has_email = self._fuzzy_column_match("email", column_names)
            has_phone = self._fuzzy_column_match("phone", column_names)
            has_address = any(
                self._fuzzy_column_match(addr, column_names)
                for addr in ["street", "address", "city", "country"]
            )

            if has_name and (has_email or has_phone or has_address):
                # Strong indication of customer data
                return 0.8

        # Calculate required column score
        required_score = required_matches / len(domain.required_columns) if domain.required_columns else 0

        # Check optional columns
        optional_matches = 0
        for optional_col in domain.optional_columns:
            if self._fuzzy_column_match(optional_col, column_names):
                optional_matches += 1

        # Calculate optional column score
        optional_score = optional_matches / len(domain.optional_columns) if domain.optional_columns else 0

        # Check data patterns for additional confidence
        pattern_boost = self._calculate_pattern_boost(domain, column_profiles)

        # Weighted score: required columns are most important
        final_score = (
            required_score * 0.6 +
            optional_score * 0.2 +
            pattern_boost * 0.2
        )

        return min(1.0, final_score)

    def _fuzzy_column_match(self, target: str, column_names: Set[str]) -> bool:
        """
        Check if target column exists in column set (fuzzy matching).

        Args:
            target: Target column name to find
            column_names: Set of actual column names

        Returns:
            True if match found
        """
        target_normalized = self._normalize_column_name(target)

        # Exact match
        if target_normalized in column_names:
            return True

        # Check if target is contained in any column
        for col in column_names:
            if target_normalized in col or col in target_normalized:
                return True

            # Token-based matching
            target_tokens = set(target_normalized.split('_'))
            col_tokens = set(col.split('_'))
            if target_tokens & col_tokens:  # Intersection
                return True

        return False

    def _calculate_pattern_boost(
        self,
        domain: DomainSignature,
        column_profiles: List[ColumnProfile]
    ) -> float:
        """
        Calculate confidence boost based on data patterns.

        Args:
            domain: Domain signature
            column_profiles: Column profiles with detected patterns

        Returns:
            Pattern boost score (0.0 to 1.0)
        """
        boost = 0.0
        pattern_count = 0

        for profile in column_profiles:
            # Check for relevant patterns based on domain
            if domain.name in ["sales_revenue", "financial_analysis", "invoices"]:
                # Look for currency patterns
                if profile.patterns.get("currency", 0) > 0.5:
                    boost += 0.2
                    pattern_count += 1

                # Look for numeric data in amount/total columns
                col_lower = profile.column_name.lower()
                if any(term in col_lower for term in ["amount", "total", "revenue", "sales"]):
                    if profile.data_type in ["integer", "float"]:
                        boost += 0.1
                        pattern_count += 1

            elif domain.name == "customer_contacts":
                # Look for email/phone patterns
                if profile.patterns.get("email", 0) > 0.5:
                    boost += 0.3
                    pattern_count += 1
                if profile.patterns.get("phone", 0) > 0.5:
                    boost += 0.2
                    pattern_count += 1

            elif domain.name == "hr_timesheet":
                # Look for date patterns and numeric hours
                if profile.patterns.get("date", 0) > 0.5:
                    boost += 0.2
                    pattern_count += 1

                col_lower = profile.column_name.lower()
                if "hour" in col_lower and profile.data_type in ["integer", "float"]:
                    boost += 0.3
                    pattern_count += 1

        # Normalize boost
        return min(1.0, boost)

    def _aggregate_model_scores(
        self,
        domain_scores: List[Tuple[DomainSignature, float]]
    ) -> Dict[str, float]:
        """
        Aggregate model scores from matching domains.

        Args:
            domain_scores: List of (DomainSignature, score) tuples

        Returns:
            Dictionary of model names to aggregated scores
        """
        model_scores = Counter()

        for domain, score in domain_scores:
            # Distribute score among models in the domain
            for model in domain.models:
                # Higher priority for models appearing first in the list
                priority_factor = 1.0 - (domain.models.index(model) * 0.1)
                model_scores[model] += score * priority_factor

        # Normalize scores
        if model_scores:
            max_score = max(model_scores.values())
            if max_score > 0:
                for model in model_scores:
                    model_scores[model] /= max_score

        return dict(model_scores)

    def detect_primary_domain(
        self,
        column_profiles: List[ColumnProfile]
    ) -> Optional[str]:
        """
        Detect the primary business domain from column profiles.

        Args:
            column_profiles: List of column profiles

        Returns:
            Name of the primary domain, or None if unclear
        """
        column_names = set(self._normalize_column_name(p.column_name) for p in column_profiles)
        domain_scores = self._score_domains(column_names, column_profiles)

        if domain_scores:
            # Return the highest scoring domain
            best_domain, best_score = max(domain_scores, key=lambda x: x[1])
            if best_score >= best_domain.confidence_threshold:
                logger.info(f"Primary domain detected: {best_domain.name} (score: {best_score:.2f})")
                return best_domain.name

        return None

    def get_recommended_models(
        self,
        column_profiles: List[ColumnProfile],
        max_models: int = 3
    ) -> List[str]:
        """
        Get a list of recommended models based on context analysis.

        Args:
            column_profiles: List of column profiles
            max_models: Maximum number of models to return

        Returns:
            List of recommended model names
        """
        model_scores = self.analyze_context(column_profiles, top_n=max_models * 2)

        # Filter to only high-confidence models
        recommended = [
            model for model, score in model_scores.items()
            if score >= 0.5
        ][:max_models]

        if not recommended and model_scores:
            # If no high-confidence models, return top scoring ones
            recommended = list(model_scores.keys())[:max_models]

        logger.info(f"Recommended models: {recommended}")
        return recommended