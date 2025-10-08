"""
Field type detection for custom Odoo fields.
Analyzes column profiles to suggest appropriate Odoo field types.
"""
from typing import Dict, Any, Optional, List


class FieldTypeDetector:
    """Detects appropriate Odoo field type from column profile data."""

    # Map data types to Odoo field types
    DTYPE_TO_ODOO = {
        "string": "Char",
        "integer": "Integer",
        "float": "Float",
        "boolean": "Boolean",
        "date": "Date",
        "datetime": "Datetime",
    }

    @classmethod
    def detect_field_type(
        cls,
        dtype_guess: str,
        patterns: Dict[str, float],
        null_pct: float,
        distinct_pct: float,
        sample_values: List[str],
    ) -> Dict[str, Any]:
        """
        Detect Odoo field type from column profile.

        Args:
            dtype_guess: Guessed data type (string, integer, float, etc.)
            patterns: Pattern detection results (email, phone, currency, etc.)
            null_pct: Percentage of null values
            distinct_pct: Percentage of distinct values
            sample_values: Sample values from the column

        Returns:
            Dict with:
                - field_type: Odoo field type (Char, Integer, Selection, etc.)
                - suggested_size: For Char fields
                - selection_options: For Selection fields
                - required: Suggested required status
                - rationale: Why this type was chosen
        """
        # Start with base type from dtype
        base_type = cls.DTYPE_TO_ODOO.get(dtype_guess, "Char")

        # Check patterns for specific field types
        if patterns:
            if patterns.get("email", 0) > 0.8:
                return {
                    "field_type": "Char",
                    "suggested_size": 255,
                    "required": null_pct < 0.1,
                    "rationale": f"Email pattern detected ({patterns['email']*100:.0f}% match)",
                }

            if patterns.get("phone", 0) > 0.8:
                return {
                    "field_type": "Char",
                    "suggested_size": 32,
                    "required": null_pct < 0.1,
                    "rationale": f"Phone pattern detected ({patterns['phone']*100:.0f}% match)",
                }

            if patterns.get("currency", 0) > 0.8:
                return {
                    "field_type": "Monetary",
                    "required": null_pct < 0.1,
                    "rationale": f"Currency pattern detected ({patterns['currency']*100:.0f}% match)",
                }

        # Check for Selection field (low distinct values)
        if distinct_pct < 0.05 and len(sample_values) > 0:
            # Extract unique values from samples
            unique_values = list(set(v for v in sample_values if v))[:20]

            if len(unique_values) <= 10:
                selection_options = [
                    {"value": val, "label": val} for val in sorted(unique_values)
                ]
                return {
                    "field_type": "Selection",
                    "selection_options": selection_options,
                    "required": null_pct < 0.1,
                    "rationale": f"Low distinct values ({distinct_pct*100:.1f}%), suggesting enum/selection",
                }

        # Check for Text vs Char based on value length
        if base_type == "Char" and sample_values:
            max_len = max((len(str(v)) for v in sample_values if v), default=0)

            if max_len > 255:
                return {
                    "field_type": "Text",
                    "required": null_pct < 0.1,
                    "rationale": f"Long text values detected (max length: {max_len})",
                }
            else:
                suggested_size = min(max(max_len + 50, 64), 255)
                return {
                    "field_type": "Char",
                    "suggested_size": suggested_size,
                    "required": null_pct < 0.1,
                    "rationale": f"Text field with max length {max_len}",
                }

        # Default to base type
        result = {
            "field_type": base_type,
            "required": null_pct < 0.1,
            "rationale": f"Based on data type: {dtype_guess}",
        }

        # Add size for Char fields
        if base_type == "Char":
            result["suggested_size"] = 255

        return result

    @classmethod
    def generate_technical_name(cls, header_name: str, prefix: str = "x_bt_") -> str:
        """
        Generate technical field name from header.

        Args:
            header_name: Original column header
            prefix: Prefix for custom fields (default: x_bt_ for Buildertrend)

        Returns:
            Valid Odoo technical field name
        """
        import re

        # Convert to lowercase
        name = header_name.lower()

        # Replace spaces and special chars with underscore
        name = re.sub(r'[^\w]+', '_', name)

        # Remove leading/trailing underscores
        name = name.strip('_')

        # Collapse multiple underscores
        name = re.sub(r'_+', '_', name)

        # Add prefix
        return f"{prefix}{name}"

    @classmethod
    def suggest_field_label(cls, header_name: str) -> str:
        """
        Generate user-friendly field label from header.

        Args:
            header_name: Original column header

        Returns:
            Cleaned field label
        """
        # Title case and clean up
        return header_name.strip().title()
