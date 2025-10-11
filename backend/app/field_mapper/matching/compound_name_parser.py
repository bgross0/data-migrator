"""
Compound Name Parser - Intelligently parse compound column names.

This module helps strategies understand column names like:
- customer_name -> (entity: customer, field: name)
- product_price -> (entity: product, field: price)
- order_date -> (entity: order, field: date)
"""
from typing import Optional, Tuple, Dict
import re

class CompoundNameParser:
    """
    Parse compound column names to extract entity hints and field names.

    This helps match columns like "customer_email" to "res.partner.email"
    by understanding that "customer" implies res.partner model.
    """

    # Entity prefixes/suffixes and their corresponding models
    ENTITY_MODEL_MAP = {
        # Contacts/Partners
        "customer": "res.partner",
        "client": "res.partner",
        "vendor": "res.partner",
        "supplier": "res.partner",
        "partner": "res.partner",
        "contact": "res.partner",
        "company": "res.partner",

        # Products
        "product": "product.product",
        "item": "product.product",
        "sku": "product.product",
        "article": "product.product",

        # Sales
        "order": "sale.order",
        "sale": "sale.order",
        "so": "sale.order",
        "quotation": "sale.order",
        "line": "sale.order.line",  # Order line items

        # Purchase
        "purchase": "purchase.order",
        "po": "purchase.order",
        "rfq": "purchase.order",

        # Invoicing
        "invoice": "account.move",
        "bill": "account.move",
        "payment": "account.payment",

        # Projects
        "project": "project.project",
        "task": "project.task",

        # Employees
        "employee": "hr.employee",
        "worker": "hr.employee",
        "staff": "hr.employee",

        # Inventory
        "stock": "stock.quant",
        "inventory": "stock.quant",
        "warehouse": "stock.warehouse",
        "location": "stock.location",
    }

    # Common field name variations
    FIELD_ALIASES = {
        "id": ["id", "code", "reference", "ref", "number", "no", "num"],
        "name": ["name", "title", "description", "desc"],
        "email": ["email", "mail", "email_address", "e_mail"],
        "phone": ["phone", "telephone", "tel", "mobile", "cell"],
        "address": ["address", "street", "addr"],
        "city": ["city", "town", "locality"],
        "country": ["country", "country_id", "nation"],
        "date": ["date", "datetime", "timestamp", "created", "updated"],
        "amount": ["amount", "total", "sum", "value"],
        "price": ["price", "cost", "rate", "fee"],
        "quantity": ["quantity", "qty", "count", "amount", "units"],
        "state": ["state", "status", "stage"],
    }

    def parse_compound_name(self, column_name: str) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Parse a compound column name into entity prefix, field name, and suggested model.

        Args:
            column_name: The column name to parse

        Returns:
            Tuple of (entity_prefix, field_name, suggested_model)

        Examples:
            "customer_name" -> ("customer", "name", "res.partner")
            "product_price" -> ("product", "price", "product.product")
            "order_quantity" -> ("order", "quantity", "sale.order.line")  # Line-level field
            "email" -> (None, "email", None)
        """
        normalized = column_name.lower().strip()

        # Try to split by common separators
        parts = re.split(r'[_\-\s]+', normalized)

        if len(parts) < 2:
            # Not a compound name
            return None, normalized, None

        # Check if first part is an entity prefix
        potential_entity = parts[0]
        if potential_entity in self.ENTITY_MODEL_MAP:
            entity_prefix = potential_entity
            field_name = '_'.join(parts[1:])
            base_model = self.ENTITY_MODEL_MAP[entity_prefix]

            # Special handling for order-related fields
            if entity_prefix in ["order", "sale", "so"] and base_model == "sale.order":
                # Check if this is a line-level field
                line_level_fields = ["quantity", "qty", "price", "unit_price",
                                   "subtotal", "total", "amount", "discount",
                                   "product", "item", "sku", "description"]
                if any(lf in field_name for lf in line_level_fields):
                    suggested_model = "sale.order.line"
                else:
                    suggested_model = base_model
            # Similar for purchase orders
            elif entity_prefix in ["purchase", "po"] and base_model == "purchase.order":
                line_level_fields = ["quantity", "qty", "price", "unit_price",
                                   "subtotal", "total", "amount", "product", "item"]
                if any(lf in field_name for lf in line_level_fields):
                    suggested_model = "purchase.order.line"
                else:
                    suggested_model = base_model
            else:
                suggested_model = base_model

            return entity_prefix, field_name, suggested_model

        # Check if last part is an entity suffix (e.g., "name_customer")
        potential_entity = parts[-1]
        if potential_entity in self.ENTITY_MODEL_MAP:
            entity_suffix = potential_entity
            field_name = '_'.join(parts[:-1])
            suggested_model = self.ENTITY_MODEL_MAP[entity_suffix]
            return entity_suffix, field_name, suggested_model

        # No entity found, return the full name as field
        return None, normalized, None

    def get_field_aliases(self, field_name: str) -> list:
        """
        Get common aliases for a field name.

        Args:
            field_name: The field name to find aliases for

        Returns:
            List of field name variations

        Example:
            "email" -> ["email", "mail", "email_address", "e_mail"]
        """
        for canonical, aliases in self.FIELD_ALIASES.items():
            if field_name in aliases:
                return aliases
        return [field_name]

    def get_model_for_entity(self, entity_name: str) -> Optional[str]:
        """
        Get the suggested Odoo model for an entity name.

        Args:
            entity_name: Entity name like "customer", "product"

        Returns:
            Odoo model name or None
        """
        return self.ENTITY_MODEL_MAP.get(entity_name.lower())

    def extract_all_hints(self, column_name: str) -> Dict[str, any]:
        """
        Extract all possible hints from a column name.

        Args:
            column_name: The column name to analyze

        Returns:
            Dictionary with parsing results
        """
        entity_prefix, field_name, suggested_model = self.parse_compound_name(column_name)
        field_aliases = self.get_field_aliases(field_name)

        return {
            "original_name": column_name,
            "entity_prefix": entity_prefix,
            "field_name": field_name,
            "suggested_model": suggested_model,
            "field_aliases": field_aliases,
            "is_compound": entity_prefix is not None,
        }