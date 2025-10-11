"""
Header matching system - maps spreadsheet column names to Odoo model fields.
Uses comprehensive field mappings based on Odoo 18 documentation.
"""
from typing import List, Dict, Any, Optional
from app.core.odoo_field_mappings import (
    get_best_match,
    detect_model_from_context,
    normalize_field_name,
    ODOO_FIELD_MAPPINGS
)


class HeaderMatcher:
    """Matches spreadsheet column headers to Odoo model fields."""

    def __init__(self, target_model: str = None):
        """
        Initialize matcher for a specific Odoo model.

        Args:
            target_model: Target Odoo model (e.g., "res.partner") or None for auto-detection
        """
        self.target_model = target_model
        self.column_names = []

    def match(self, header: str, sheet_name: Optional[str] = None, column_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate ranked mapping suggestions for a header.

        Args:
            header: Column header name
            sheet_name: Optional sheet name for model detection
            column_names: Optional list of all column names for better model detection

        Returns:
            List of candidates: [{model, field, confidence, method, rationale}]
        """
        # Store column names for model detection
        if column_names:
            self.column_names = column_names

        # Auto-detect model if not specified
        if not self.target_model:
            self.target_model = detect_model_from_context(sheet_name or "", self.column_names or [header])

        candidates = []

        # Try primary model first
        field, confidence, rationale = get_best_match(header, self.target_model)
        if field:
            candidates.append({
                "model": self.target_model,
                "field": field,
                "confidence": confidence,
                "method": "field_mapping",
                "rationale": rationale
            })

        # Also try other likely models if confidence is not perfect
        if confidence < 1.0:
            alternative_models = self._get_alternative_models(header, sheet_name)
            for alt_model in alternative_models:
                if alt_model != self.target_model:
                    alt_field, alt_confidence, alt_rationale = get_best_match(header, alt_model)
                    if alt_field and alt_confidence > 0.5:
                        candidates.append({
                            "model": alt_model,
                            "field": alt_field,
                            "confidence": alt_confidence * 0.9,  # Slightly lower for alternative models
                            "method": "alternative_model",
                            "rationale": alt_rationale
                        })

        # Sort by confidence
        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # If no matches found, provide a generic fallback
        if not candidates:
            candidates.append({
                "model": self.target_model,
                "field": None,
                "confidence": 0.0,
                "method": "no_match",
                "rationale": f"No suitable field found in {self.target_model} for '{header}'"
            })

        return candidates[:5]  # Top 5

    def _get_alternative_models(self, header: str, sheet_name: str = None) -> List[str]:
        """Get alternative models that might contain this field."""
        header_lower = header.lower()
        alternatives = []

        # Check which models might have this field
        for model_name in ODOO_FIELD_MAPPINGS:
            if model_name != self.target_model:
                # Check if any field patterns match
                for field_name, patterns in ODOO_FIELD_MAPPINGS[model_name].items():
                    for pattern in patterns:
                        if pattern.lower() in header_lower or header_lower in pattern.lower():
                            if model_name not in alternatives:
                                alternatives.append(model_name)
                            break

        # Prioritize certain models based on context
        priority_models = []

        # If it looks like customer data, prioritize res.partner
        if any(word in header_lower for word in ["customer", "client", "vendor", "supplier", "contact", "company"]):
            priority_models.append("res.partner")

        # If it looks like product data, prioritize product.product
        if any(word in header_lower for word in ["product", "item", "sku", "price", "cost"]):
            priority_models.append("product.product")

        # If it looks like sales data, prioritize sale.order
        if any(word in header_lower for word in ["order", "sale", "quotation"]):
            priority_models.append("sale.order")

        # If it looks like lead data, prioritize crm.lead
        if any(word in header_lower for word in ["lead", "opportunity", "pipeline", "stage"]):
            priority_models.append("crm.lead")

        # Combine priority models with alternatives
        final_alternatives = []
        for model in priority_models:
            if model in alternatives and model not in final_alternatives:
                final_alternatives.append(model)

        for model in alternatives:
            if model not in final_alternatives:
                final_alternatives.append(model)

        return final_alternatives[:3]  # Return top 3 alternatives