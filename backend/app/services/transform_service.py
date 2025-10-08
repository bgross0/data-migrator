"""Transform functions for data cleaning and normalization."""

import re
from datetime import datetime
from typing import Any, Optional
import phonenumbers


class TransformService:
    """Service for applying transforms to data values."""

    AVAILABLE_TRANSFORMS = {
        # String transforms
        "trim": {
            "name": "Trim Whitespace",
            "description": "Remove leading and trailing whitespace",
            "params": []
        },
        "uppercase": {
            "name": "Uppercase",
            "description": "Convert to uppercase",
            "params": []
        },
        "lowercase": {
            "name": "Lowercase",
            "description": "Convert to lowercase",
            "params": []
        },
        "title_case": {
            "name": "Title Case",
            "description": "Convert to title case",
            "params": []
        },
        "strip_special": {
            "name": "Strip Special Characters",
            "description": "Remove special characters, keeping only alphanumeric",
            "params": []
        },
        "replace": {
            "name": "Find and Replace",
            "description": "Replace occurrences of a pattern",
            "params": [
                {"name": "find", "type": "string", "required": True},
                {"name": "replace", "type": "string", "required": True}
            ]
        },

        # Phone number transforms
        "phone_normalize": {
            "name": "Normalize Phone Number",
            "description": "Format phone number to E.164 standard",
            "params": [
                {"name": "country", "type": "string", "required": False, "default": "US"}
            ]
        },

        # Date transforms
        "parse_date": {
            "name": "Parse Date",
            "description": "Parse date from string format",
            "params": [
                {"name": "format", "type": "string", "required": True, "default": "%Y-%m-%d"}
            ]
        },

        # Number transforms
        "round": {
            "name": "Round Number",
            "description": "Round to specified decimal places",
            "params": [
                {"name": "decimals", "type": "integer", "required": False, "default": 0}
            ]
        },

        # Boolean transforms
        "parse_bool": {
            "name": "Parse Boolean",
            "description": "Convert yes/no, true/false, 1/0 to boolean",
            "params": []
        },

        # Default value
        "default_if_empty": {
            "name": "Default If Empty",
            "description": "Set default value if empty or null",
            "params": [
                {"name": "default", "type": "string", "required": True}
            ]
        },

        # Prefix/Suffix
        "add_prefix": {
            "name": "Add Prefix",
            "description": "Add prefix to value",
            "params": [
                {"name": "prefix", "type": "string", "required": True}
            ]
        },
        "add_suffix": {
            "name": "Add Suffix",
            "description": "Add suffix to value",
            "params": [
                {"name": "suffix", "type": "string", "required": True}
            ]
        },

        # Many2many / List transforms
        "split": {
            "name": "Split String",
            "description": "Split string into list by delimiter (for many2many fields)",
            "params": [
                {"name": "delimiter", "type": "string", "required": False, "default": ";"}
            ]
        },
        "map": {
            "name": "Map to External IDs",
            "description": "Map values to external IDs using lookup table (generates lookup CSV on export)",
            "params": [
                {"name": "table", "type": "string", "required": True, "description": "Lookup table name"}
            ]
        },
    }

    @classmethod
    def apply_transform(cls, value: Any, fn: str, params: Optional[dict] = None) -> Any:
        """Apply a single transform to a value."""
        if value is None:
            if fn == "default_if_empty":
                return params.get("default", "")
            return None

        params = params or {}

        # String transforms
        if fn == "trim":
            return str(value).strip()

        elif fn == "uppercase":
            return str(value).upper()

        elif fn == "lowercase":
            return str(value).lower()

        elif fn == "title_case":
            return str(value).title()

        elif fn == "strip_special":
            return re.sub(r'[^a-zA-Z0-9\s]', '', str(value))

        elif fn == "replace":
            find = params.get("find", "")
            replace = params.get("replace", "")
            return str(value).replace(find, replace)

        # Phone number
        elif fn == "phone_normalize":
            try:
                country = params.get("country", "US")
                parsed = phonenumbers.parse(str(value), country)
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            except:
                return str(value)  # Return original if parsing fails

        # Date parsing
        elif fn == "parse_date":
            try:
                date_format = params.get("format", "%Y-%m-%d")
                parsed_date = datetime.strptime(str(value), date_format)
                return parsed_date.strftime("%Y-%m-%d")  # Return ISO format
            except:
                return str(value)  # Return original if parsing fails

        # Number transforms
        elif fn == "round":
            try:
                decimals = params.get("decimals", 0)
                return round(float(value), decimals)
            except:
                return value

        # Boolean
        elif fn == "parse_bool":
            val = str(value).lower().strip()
            if val in ["yes", "true", "1", "y", "t"]:
                return True
            elif val in ["no", "false", "0", "n", "f"]:
                return False
            return None

        # Default value
        elif fn == "default_if_empty":
            if not str(value).strip():
                return params.get("default", "")
            return value

        # Prefix/Suffix
        elif fn == "add_prefix":
            prefix = params.get("prefix", "")
            return f"{prefix}{value}"

        elif fn == "add_suffix":
            suffix = params.get("suffix", "")
            return f"{value}{suffix}"

        # Many2many / List transforms
        elif fn == "split":
            delimiter = params.get("delimiter", ";")
            # Split and trim each item
            items = [item.strip() for item in str(value).split(delimiter) if item.strip()]
            # Return as LIST (next transform in chain can process it)
            return items

        elif fn == "map":
            # Map values to external IDs
            table_name = params.get("table")

            if not table_name:
                return value

            if isinstance(value, list):
                # Map each item in list to external ID
                mapped = []
                for item in value:
                    sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', str(item))
                    external_id = f"migr.{table_name}.{sanitized}"
                    mapped.append(external_id)
                return mapped  # Return list of external IDs
            else:
                # Single value
                sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', str(value))
                return f"migr.{table_name}.{sanitized}"

        return value

    @classmethod
    def apply_transforms(cls, value: Any, transforms: list) -> Any:
        """Apply a chain of transforms to a value."""
        result = value
        for transform in transforms:
            fn = transform.get("fn")
            params = transform.get("params", {})
            result = cls.apply_transform(result, fn, params)
        return result

    @classmethod
    def get_available_transforms(cls):
        """Get list of available transform functions with metadata."""
        return cls.AVAILABLE_TRANSFORMS
