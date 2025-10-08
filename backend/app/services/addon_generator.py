"""
Odoo addon generator - Creates installable Odoo modules for custom fields.
"""
import os
import zipfile
from io import BytesIO
from typing import Dict, List
from sqlalchemy.orm import Session
from app.models import Mapping
from app.models.mapping import MappingStatus


class OdooAddonGenerator:
    """Generates Odoo addon modules from custom field definitions."""

    def __init__(self, db: Session):
        self.db = db

    def generate_addon(self, dataset_id: int, addon_name: str = "custom_fields_migration") -> BytesIO:
        """
        Generate Odoo addon module as .zip file.

        Args:
            dataset_id: Dataset ID to generate addon for
            addon_name: Technical name for the addon module

        Returns:
            BytesIO containing the .zip file
        """
        # Get all CREATE_FIELD mappings for this dataset
        custom_fields = self.db.query(Mapping).filter(
            Mapping.dataset_id == dataset_id,
            Mapping.status == MappingStatus.CREATE_FIELD
        ).all()

        if not custom_fields:
            raise ValueError("No custom fields defined for this dataset")

        # Group fields by model
        fields_by_model = {}
        for mapping in custom_fields:
            model = mapping.target_model
            if not model:
                continue

            if model not in fields_by_model:
                fields_by_model[model] = []

            fields_by_model[model].append({
                "name": mapping.custom_field_definition.get("technical_name"),
                "label": mapping.custom_field_definition.get("field_label"),
                "type": mapping.custom_field_definition.get("field_type"),
                "required": mapping.custom_field_definition.get("required", False),
                "size": mapping.custom_field_definition.get("size"),
                "help": mapping.custom_field_definition.get("help_text"),
                "selection": mapping.custom_field_definition.get("selection_options"),
                "related_model": mapping.custom_field_definition.get("related_model"),
            })

        # Create addon structure in memory
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Generate module files
            self._write_manifest(zipf, addon_name, fields_by_model)
            self._write_init_files(zipf, addon_name, fields_by_model)
            self._write_model_files(zipf, addon_name, fields_by_model)

        zip_buffer.seek(0)
        return zip_buffer

    def _write_manifest(self, zipf: zipfile.ZipFile, addon_name: str, fields_by_model: Dict):
        """Write __manifest__.py file."""
        manifest_content = f'''# -*- coding: utf-8 -*-
{{
    'name': 'Custom Fields Migration',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Custom fields for data migration',
    'description': """
Custom Fields Migration
=======================
This module adds custom fields to support data migration from external systems.

Models extended:
{chr(10).join(f'- {model}' for model in fields_by_model.keys())}
    """,
    'author': 'Data Migration Tool',
    'depends': ['base', 'crm', 'sale', 'project', 'hr', 'account', 'stock'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}}
'''
        zipf.writestr(f'{addon_name}/__manifest__.py', manifest_content)

    def _write_init_files(self, zipf: zipfile.ZipFile, addon_name: str, fields_by_model: Dict):
        """Write __init__.py files."""
        # Root __init__.py
        root_init = "from . import models\n"
        zipf.writestr(f'{addon_name}/__init__.py', root_init)

        # Models __init__.py
        model_imports = []
        for model in fields_by_model.keys():
            model_file = model.replace('.', '_')
            model_imports.append(f"from . import {model_file}")

        models_init = "\n".join(model_imports) + "\n"
        zipf.writestr(f'{addon_name}/models/__init__.py', models_init)

    def _write_model_files(self, zipf: zipfile.ZipFile, addon_name: str, fields_by_model: Dict):
        """Write model inheritance files."""
        for model, fields in fields_by_model.items():
            model_file = model.replace('.', '_')
            model_class = ''.join(word.capitalize() for word in model.replace('.', '_').split('_'))

            # Generate field definitions
            field_defs = []
            for field in fields:
                field_def = self._generate_field_definition(field)
                field_defs.append(field_def)

            model_content = f'''# -*- coding: utf-8 -*-
from odoo import models, fields

class {model_class}(models.Model):
    _inherit = '{model}'

{chr(10).join(field_defs)}
'''
            zipf.writestr(f'{addon_name}/models/{model_file}.py', model_content)

    def _generate_field_definition(self, field_spec: Dict) -> str:
        """Generate Odoo field definition code."""
        field_name = field_spec["name"]
        field_type = field_spec["type"]
        field_label = field_spec["label"]
        required = field_spec.get("required", False)
        help_text = field_spec.get("help")
        size = field_spec.get("size")
        selection = field_spec.get("selection")
        related_model = field_spec.get("related_model")

        # Build field parameters
        params = [f"string='{field_label}'"]

        if required:
            params.append("required=True")

        if help_text:
            params.append(f"help='{help_text}'")

        # Type-specific parameters
        if field_type == "Char" and size:
            params.append(f"size={size}")

        if field_type == "Selection" and selection:
            options = [(opt["value"], opt["label"]) for opt in selection]
            params.append(f"selection={options}")

        if field_type == "Many2one" and related_model:
            params.insert(0, f"'{related_model}'")

        params_str = ", ".join(params)

        return f"    {field_name} = fields.{field_type}({params_str})"

    def get_installation_instructions(self, addon_name: str) -> str:
        """Get installation instructions for the generated addon."""
        return f"""
Installation Instructions
=========================

1. Extract the downloaded {addon_name}.zip file

2. Copy the {addon_name} folder to your Odoo addons directory:
   - For Odoo.sh: Upload via the addons manager
   - For local installations: Copy to /path/to/odoo/addons/ or custom addons path

3. Update the apps list:
   - Go to Apps menu
   - Click "Update Apps List" (developer mode required)

4. Install the module:
   - Search for "Custom Fields Migration"
   - Click "Install"

5. Verify installation:
   - Check that custom fields appear in the respective forms
   - All fields will be prefixed with "x_" (Odoo custom field convention)

6. Proceed with data import using the configured mappings

Note: This module must be installed BEFORE running the data import.
"""
