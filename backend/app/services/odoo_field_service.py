"""
Service for creating custom fields in Odoo via XML-RPC.
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models import Mapping
from app.models.mapping import MappingStatus
from app.connectors.odoo import OdooConnector


class OdooFieldService:
    """Service for creating custom fields in Odoo."""

    # Mapping from our field types to Odoo field types
    FIELD_TYPE_MAPPING = {
        "Char": "char",
        "Integer": "integer",
        "Float": "float",
        "Boolean": "boolean",
        "Date": "date",
        "Datetime": "datetime",
        "Text": "text",
        "Html": "html",
        "Selection": "selection",
        "Many2one": "many2one",
        "Monetary": "monetary",
    }

    def __init__(self, db: Session):
        self.db = db

    def create_custom_fields_for_dataset(
        self,
        dataset_id: int,
        odoo_connector: OdooConnector
    ) -> Dict[str, Any]:
        """
        Create all custom fields for a dataset in Odoo.

        Args:
            dataset_id: Dataset ID
            odoo_connector: Configured OdooConnector instance

        Returns:
            Dict with results: {
                "success": bool,
                "created": int,
                "failed": int,
                "results": [{"mapping_id", "field_name", "status", "message"}]
            }
        """
        # Get all CREATE_FIELD mappings for this dataset
        custom_fields = self.db.query(Mapping).filter(
            Mapping.dataset_id == dataset_id,
            Mapping.status == MappingStatus.CREATE_FIELD
        ).all()

        if not custom_fields:
            return {
                "success": False,
                "created": 0,
                "failed": 0,
                "message": "No custom fields defined for this dataset",
                "results": []
            }

        results = []
        created_count = 0
        failed_count = 0

        for mapping in custom_fields:
            try:
                field_id = self._create_field_from_mapping(mapping, odoo_connector)
                created_count += 1
                results.append({
                    "mapping_id": mapping.id,
                    "field_name": mapping.custom_field_definition.get("technical_name"),
                    "field_label": mapping.custom_field_definition.get("field_label"),
                    "model": mapping.target_model,
                    "status": "created",
                    "field_id": field_id,
                    "message": "Field created successfully"
                })

                # Update mapping status (optionally add a new status like "field_created")
                # For now we'll keep it as CREATE_FIELD but could add metadata

            except Exception as e:
                failed_count += 1
                results.append({
                    "mapping_id": mapping.id,
                    "field_name": mapping.custom_field_definition.get("technical_name"),
                    "model": mapping.target_model,
                    "status": "failed",
                    "message": str(e)
                })

        return {
            "success": failed_count == 0,
            "created": created_count,
            "failed": failed_count,
            "total": len(custom_fields),
            "results": results
        }

    def _create_field_from_mapping(
        self,
        mapping: Mapping,
        odoo_connector: OdooConnector
    ) -> int:
        """
        Create a single custom field in Odoo from a mapping.

        Args:
            mapping: Mapping with custom_field_definition
            odoo_connector: Configured OdooConnector

        Returns:
            Field ID in Odoo

        Raises:
            Exception: If field creation fails
        """
        if not mapping.custom_field_definition:
            raise ValueError("Mapping has no custom field definition")

        if not mapping.target_model:
            raise ValueError("Mapping has no target model")

        field_def = mapping.custom_field_definition

        # Translate field definition to Odoo parameters
        params = self._translate_field_definition(field_def)

        # Create the field
        field_id = odoo_connector.create_custom_field(
            model_name=mapping.target_model,
            field_name=field_def["technical_name"],
            field_label=field_def["field_label"],
            field_type=params["field_type"],
            required=field_def.get("required", False),
            **params.get("extra", {})
        )

        return field_id

    def _translate_field_definition(
        self,
        field_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate CustomFieldDefinition to Odoo field parameters.

        Args:
            field_def: CustomFieldDefinition dict

        Returns:
            Dict with "field_type" and "extra" params
        """
        field_type = field_def.get("field_type", "Char")
        odoo_field_type = self.FIELD_TYPE_MAPPING.get(field_type, "char")

        extra_params = {}

        # Add help text
        if field_def.get("help_text"):
            extra_params["help"] = field_def["help_text"]

        # Type-specific parameters
        if field_type == "Char" and field_def.get("size"):
            extra_params["size"] = field_def["size"]

        elif field_type == "Selection" and field_def.get("selection_options"):
            # Convert selection options to Odoo format
            # Odoo expects: [('value1', 'Label 1'), ('value2', 'Label 2')]
            selection = [
                (opt["value"], opt["label"])
                for opt in field_def["selection_options"]
            ]
            extra_params["selection"] = selection

        elif field_type == "Many2one" and field_def.get("related_model"):
            extra_params["relation"] = field_def["related_model"]

        return {
            "field_type": odoo_field_type,
            "extra": extra_params
        }
