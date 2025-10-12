"""
Hybrid Matcher - Best of both worlds.

Combines:
- BusinessContextAnalyzer (intelligent model detection)
- OdooKnowledgeBase (authoritative field metadata)
- Hardcoded patterns (deterministic, proven matches)

Without the noise:
- No 8-strategy architecture
- No CellDataAnalyzer interference
- No type-only matching
- No strategy merging/dilution

Simple, linear flow:
1. Detect primary model (BusinessContextAnalyzer)
2. Try pattern match (hardcoded patterns)
3. Validate with knowledge base
4. Fallback to KB lookups
5. Return single best match
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re

# Import the good parts
from app.field_mapper.matching.business_context_analyzer import BusinessContextAnalyzer
from app.field_mapper.core.knowledge_base import OdooKnowledgeBase
from app.field_mapper.core.data_structures import ColumnProfile
from app.field_mapper.core.module_registry import get_module_registry
from app.core.odoo_field_mappings import ODOO_FIELD_MAPPINGS


class HybridMatcher:
    """
    Hybrid matcher combining intelligent context detection with deterministic patterns.

    This matcher cherry-picks the best components:
    - BusinessContextAnalyzer for model detection
    - OdooKnowledgeBase for field validation
    - Hardcoded patterns for proven matches

    It avoids the pitfalls:
    - No multi-strategy interference
    - No type-only matching
    - No fuzzy noise
    """

    def __init__(self, dictionary_path: Optional[Path] = None):
        """
        Initialize the hybrid matcher.

        Args:
            dictionary_path: Path to odoo-dictionary folder (5 Excel files)
        """
        # Initialize BusinessContextAnalyzer for model detection
        self.business_analyzer = BusinessContextAnalyzer()

        # Load OdooKnowledgeBase if path provided
        self.knowledge_base = None
        if dictionary_path and Path(dictionary_path).exists():
            try:
                self.knowledge_base = OdooKnowledgeBase(dictionary_path=dictionary_path)
                self.knowledge_base.load_from_dictionary()
                print(f"✓ Loaded knowledge base: {len(self.knowledge_base.models)} models, {len(self.knowledge_base.fields)} fields")
            except Exception as e:
                print(f"⚠ Could not load knowledge base: {e}")
                self.knowledge_base = None

        # Import hardcoded patterns from simple matcher
        self.patterns = ODOO_FIELD_MAPPINGS

    def match(
        self,
        header: str,
        sheet_name: Optional[str] = None,
        column_names: Optional[List[str]] = None,
        selected_modules: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate ranked mapping suggestions for a header.

        Args:
            header: Column header name
            sheet_name: Optional sheet name for context
            column_names: Optional list of all column names for model detection
            selected_modules: Optional list of module names to constrain model search

        Returns:
            List of candidates: [{model, field, confidence, method, rationale}]
        """
        if column_names is None:
            column_names = [header]

        # Step 1: Detect primary model using BusinessContextAnalyzer
        primary_model = self._detect_primary_model(column_names, sheet_name, selected_modules)

        # Step 2: Try pattern match (hardcoded patterns from simple matcher)
        pattern_match = self._pattern_match(header, primary_model)
        if pattern_match:
            return [pattern_match]

        # Step 3: Try knowledge base lookups (if available)
        if self.knowledge_base:
            kb_matches = self._knowledge_base_lookup(header, primary_model)
            if kb_matches:
                return kb_matches

        # Step 4: No match found
        return [{
            "model": primary_model,
            "field": None,
            "confidence": 0.0,
            "method": "no_match",
            "rationale": f"No suitable field found in {primary_model} for '{header}'"
        }]

    def _detect_primary_model(
        self,
        column_names: List[str],
        sheet_name: Optional[str] = None,
        selected_modules: Optional[List[str]] = None
    ) -> str:
        """
        Detect the primary model for this sheet.

        Uses BusinessContextAnalyzer with domain signatures, optionally
        constrained to selected modules.

        Args:
            column_names: List of all column names in the sheet
            sheet_name: Optional sheet name
            selected_modules: Optional list of module names to constrain search

        Returns:
            Primary model name (e.g., "res.partner")
        """
        # Get allowed models from selected modules if provided
        allowed_models = None
        if selected_modules:
            registry = get_module_registry()
            allowed_models = registry.get_models_for_groups(selected_modules)
            print(f"🎯 Constraining model detection to {len(allowed_models)} models from modules: {selected_modules}")

        # Create minimal column profiles for BusinessContextAnalyzer
        # It only needs column names for domain detection
        column_profiles = [
            ColumnProfile(
                column_name=col,
                data_type="string",
                sample_values=[],
                total_rows=0,
                non_null_count=0,
                unique_count=0,
                null_percentage=0.0,
                uniqueness_ratio=0.0,
                patterns={},
                sheet_name=sheet_name or "Sheet1"
            )
            for col in column_names
        ]

        # Get recommended models from BusinessContextAnalyzer
        recommended = self.business_analyzer.get_recommended_models(
            column_profiles,
            max_models=5  # Get more options to filter
        )

        # Filter by allowed models if specified
        if recommended and allowed_models:
            filtered = [m for m in recommended if m in allowed_models]
            if filtered:
                print(f"✓ Filtered to allowed model: {filtered[0]}")
                return filtered[0]
            else:
                print(f"⚠ No recommended models match selected modules, using fallback heuristics")

        if recommended:
            return recommended[0]

        # Fallback: Try simple heuristics based on column names
        col_names_lower = [c.lower() for c in column_names]
        col_names_joined = ' '.join(col_names_lower)

        # Helper to check if model is allowed
        def is_allowed(model: str) -> bool:
            return allowed_models is None or model in allowed_models

        # Check for specific models FIRST (before generic ones)
        # Order matters: most specific first, most generic last

        # Fleet/Vehicle indicators (very specific)
        if is_allowed("fleet.vehicle") and any(ind in col_names_joined for ind in ["vin", "license plate", "vehicle", "odometer", "driver"]):
            return "fleet.vehicle"

        # Lead/CRM indicators (specific)
        if is_allowed("crm.lead"):
            lead_count = sum(1 for ind in ["opportunity", "lead", "expected revenue", "source"] if ind in col_names_joined)
            if lead_count >= 2 or "opportunity" in col_names_joined:
                return "crm.lead"

        # Project indicators (specific)
        if is_allowed("project.project"):
            project_count = sum(1 for ind in ["project", "deadline"] if ind in col_names_joined)
            if project_count >= 2 or ("project" in col_names_joined and "manager" in col_names_joined):
                return "project.project"

        # Task indicators (specific)
        if is_allowed("project.task"):
            task_count = sum(1 for ind in ["task", "assigned", "priority"] if ind in col_names_joined)
            if task_count >= 2:
                return "project.task"

        # Invoice indicators (check before order - invoices have "due date")
        if is_allowed("account.move"):
            invoice_count = sum(1 for ind in ["invoice", "due date", "bill"] if ind in col_names_joined)
            if invoice_count >= 2 or "invoice" in col_names_joined:
                return "account.move"

        # Sale order line indicators (check before sale order)
        if is_allowed("sale.order.line") and "order" in col_names_joined and "quantity" in col_names_joined and ("unit price" in col_names_joined or "discount" in col_names_joined):
            return "sale.order.line"

        # Sales order indicators
        if is_allowed("sale.order"):
            order_count = sum(1 for ind in ["order", "sale", "salesperson"] if ind in col_names_joined)
            if order_count >= 2 or ("order" in col_names_joined and "customer" in col_names_joined):
                return "sale.order"

        # Analytic/Financial indicators (specific)
        if is_allowed("account.analytic.line"):
            if "segment" in col_names_joined or "analytic" in col_names_joined:
                if "revenue" in col_names_joined or "profit" in col_names_joined or "cogs" in col_names_joined:
                    return "account.analytic.line"

        # Product indicators (check AFTER more specific models)
        if is_allowed("product.product"):
            product_count = sum(1 for ind in ["product", "sku", "barcode"] if ind in col_names_joined)
            if product_count >= 2:
                return "product.product"
            # Only use generic "price"/"cost" if combined with product-specific terms
            if ("sku" in col_names_joined or "barcode" in col_names_joined) and ("price" in col_names_joined or "cost" in col_names_joined):
                return "product.product"

        # Default to res.partner (most common) if allowed, otherwise use first allowed model
        if is_allowed("res.partner"):
            return "res.partner"
        elif allowed_models:
            # Use first allowed model as fallback
            fallback = list(allowed_models)[0]
            print(f"⚠ Falling back to first allowed model: {fallback}")
            return fallback
        else:
            return "res.partner"

    def _pattern_match(
        self,
        header: str,
        primary_model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Try to match using hardcoded patterns from simple matcher.

        Args:
            header: Column header name
            primary_model: Primary model detected

        Returns:
            Match dict or None
        """
        if primary_model not in self.patterns:
            return None

        # Normalize header for matching
        header_normalized = self._normalize(header)

        # Get patterns for this model
        model_patterns = self.patterns[primary_model]

        # PRIORITY 1: Check if header matches field name exactly (e.g., "is_company" → is_company field)
        # This prevents substring conflicts like "company" pattern matching "is_company" header
        if header_normalized in model_patterns:
            field_name = header_normalized
            is_valid = self._validate_field(primary_model, field_name)
            return {
                "model": primary_model,
                "field": field_name,
                "confidence": 1.0,  # Highest confidence for exact field name match
                "method": "exact_field_name",
                "rationale": f"Exact field name match: '{header}' → '{field_name}'" + ("" if is_valid else " (KB validation unavailable)")
            }

        # PRIORITY 2: Try exact pattern match (e.g., "Customer Name" → "name" pattern → name field)
        for field_name, pattern_list in model_patterns.items():
            for pattern in pattern_list:
                pattern_normalized = self._normalize(pattern)

                # Exact match
                if header_normalized == pattern_normalized:
                    # IMPORTANT: Trust hardcoded patterns even if KB validation fails
                    # Patterns are curated and more reliable than KB lookups
                    # Only do soft validation (warn but don't reject)
                    is_valid = self._validate_field(primary_model, field_name)
                    return {
                        "model": primary_model,
                        "field": field_name,
                        "confidence": 1.0,  # Highest confidence for exact pattern match
                        "method": "exact_pattern",
                        "rationale": f"Exact pattern match: '{header}' → '{field_name}'" + ("" if is_valid else " (KB validation unavailable)")
                    }

        # PRIORITY 3: Try substring match (e.g., "Customer Email Address" contains "email" pattern)
        for field_name, pattern_list in model_patterns.items():
            for pattern in pattern_list:
                pattern_normalized = self._normalize(pattern)

                # Substring match
                if pattern_normalized in header_normalized or header_normalized in pattern_normalized:
                    # Trust patterns but with slightly lower confidence
                    is_valid = self._validate_field(primary_model, field_name)
                    return {
                        "model": primary_model,
                        "field": field_name,
                        "confidence": 0.90,  # High confidence for substring match (boosted from 0.85)
                        "method": "substring_pattern",
                        "rationale": f"Substring pattern match: '{header}' contains/matches '{pattern}' → '{field_name}'" + ("" if is_valid else " (KB validation unavailable)")
                    }

        return None

    def _knowledge_base_lookup(
        self,
        header: str,
        primary_model: str
    ) -> List[Dict[str, Any]]:
        """
        Lookup in knowledge base using labels and field names.

        Args:
            header: Column header name
            primary_model: Primary model

        Returns:
            List of matches from knowledge base
        """
        if not self.knowledge_base:
            return []

        matches = []
        header_normalized = self._normalize(header)

        # Try label lookup
        label_matches = self.knowledge_base.lookup_by_label(header_normalized)
        for model_name, field_name in label_matches:
            if model_name == primary_model:
                matches.append({
                    "model": model_name,
                    "field": field_name,
                    "confidence": 0.95,
                    "method": "kb_label",
                    "rationale": f"Knowledge base label match: '{header}' → {model_name}.{field_name}"
                })

        # Try field name lookup
        if not matches:
            field_matches = self.knowledge_base.lookup_by_field_name(header_normalized)
            for model_name, field_name in field_matches:
                if model_name == primary_model:
                    matches.append({
                        "model": model_name,
                        "field": field_name,
                        "confidence": 0.90,
                        "method": "kb_field_name",
                        "rationale": f"Knowledge base field name match: '{header}' → {model_name}.{field_name}"
                    })

        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[:5]  # Top 5

    def _validate_field(self, model: str, field: str) -> bool:
        """
        Validate that a field exists in the model (using knowledge base).

        Args:
            model: Model name
            field: Field name

        Returns:
            True if field exists or KB not available (optimistic)
        """
        if not self.knowledge_base:
            return True  # Optimistic: assume it exists if we can't validate

        # Custom fields (x_*) are always valid (not in standard KB)
        if field.startswith('x_'):
            return True

        # If model doesn't exist in KB, trust the patterns (for specialized models like fleet.vehicle)
        if model not in self.knowledge_base.models:
            return True

        # Check if field exists in knowledge base for standard models/fields
        field_def = self.knowledge_base.fields.get((model, field))
        return field_def is not None

    def _normalize(self, text: str) -> str:
        """
        Normalize text for matching: lowercase, remove punctuation, trim.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        text = text.lower().strip()
        # Remove common punctuation but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
