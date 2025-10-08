"""
Export service for converting data-migrator datasets to odoo-migrate format.

This service transforms interactive cleanup work into deterministic file-based configs:
- Applies all configured transforms to source data
- Exports CLEANED CSV files (transforms already applied)
- Generates YAML mappings WITHOUT transforms (since data is already clean)
- Creates lookup tables for many2many relationships
- Detects external ID patterns from unique keys
"""

import io
import yaml
import pandas as pd
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session, joinedload

from app.models import Dataset, Sheet, Mapping, Transform, ColumnProfile, Relationship
from app.services.transform_service import TransformService


class OdooMigrateExportService:
    """Service for exporting data-migrator datasets to odoo-migrate format."""

    def __init__(self, db: Session):
        self.db = db
        self.transform_service = TransformService()

    async def export_dataset(self, dataset_id: int) -> bytes:
        """
        Export complete dataset to odoo-migrate format.

        Returns:
            ZIP file as bytes containing:
            - config/mappings/*.yml (field mappings, NO transforms)
            - config/lookups/*.csv (relationship lookups)
            - config/ids.yml (external ID patterns)
            - config/project.yml (project config)
            - data/raw/*.csv (CLEANED data with transforms applied)
        """
        # Load dataset with all relationships
        dataset = self._load_dataset_with_relations(dataset_id)

        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Generate and add all config files
            self._add_config_files(zip_file, dataset)

            # Generate and add cleaned CSV files
            self._add_cleaned_csv_files(zip_file, dataset)

        zip_buffer.seek(0)
        return zip_buffer.read()

    def _load_dataset_with_relations(self, dataset_id: int) -> Optional[Dataset]:
        """Load dataset with all necessary relationships."""
        return self.db.query(Dataset)\
            .options(
                joinedload(Dataset.source_file),
                joinedload(Dataset.sheets)
                    .joinedload(Sheet.column_profiles),
                joinedload(Dataset.sheets)
                    .joinedload(Sheet.mappings)
                    .joinedload(Mapping.transforms),
            )\
            .filter(Dataset.id == dataset_id)\
            .first()

    def _add_config_files(self, zip_file: zipfile.ZipFile, dataset: Dataset) -> None:
        """Generate and add all configuration files to ZIP."""

        # Group mappings by target model
        mappings_by_model = self._group_mappings_by_model(dataset)

        # Generate external ID patterns
        id_patterns = self._generate_id_patterns(dataset, mappings_by_model)

        # Add project.yml
        project_config = self._generate_project_config()
        zip_file.writestr('config/project.yml', yaml.dump(project_config, sort_keys=False))

        # Add ids.yml
        ids_config = {
            'default_namespace': 'migr',
            'patterns': id_patterns
        }
        zip_file.writestr('config/ids.yml', yaml.dump(ids_config, sort_keys=False))

        # Add mapping YAML files for each model
        for model, mappings in mappings_by_model.items():
            yaml_content = self._generate_yaml_mapping(
                model,
                mappings,
                id_patterns.get(model, f"migr.{model.replace('.', '_')}.{{_index}}")
            )
            zip_file.writestr(
                f'config/mappings/{model}.yml',
                yaml.dump(yaml_content, sort_keys=False, allow_unicode=True)
            )

        # Add lookup tables if any many2many relationships exist
        lookup_tables = self._generate_lookup_tables(dataset)
        for lookup_name, lookup_df in lookup_tables.items():
            csv_content = lookup_df.to_csv(index=False)
            zip_file.writestr(f'config/lookups/{lookup_name}.csv', csv_content)

    def _add_cleaned_csv_files(self, zip_file: zipfile.ZipFile, dataset: Dataset) -> None:
        """Generate cleaned CSV files with transforms already applied."""

        for sheet in dataset.sheets:
            # Get chosen mappings for this sheet
            chosen_mappings = [m for m in sheet.mappings if m.chosen]

            if not chosen_mappings:
                continue

            # Apply transforms and get cleaned dataframe
            cleaned_df = self._apply_transforms_to_sheet(dataset, sheet, chosen_mappings)

            # Determine filename from sheet name or model
            target_models = list(set(m.target_model for m in chosen_mappings if m.target_model))
            if target_models:
                filename = f"{target_models[0]}.csv"
            else:
                filename = f"{sheet.name.replace(' ', '_').lower()}.csv"

            # Export to CSV
            csv_content = cleaned_df.to_csv(index=False)
            zip_file.writestr(f'data/raw/{filename}', csv_content)

    def _apply_transforms_to_sheet(
        self,
        dataset: Dataset,
        sheet: Sheet,
        mappings: List[Mapping]
    ) -> pd.DataFrame:
        """
        Read source file and apply all configured transforms.

        Returns cleaned dataframe with transforms applied.
        """
        # Read source file
        file_path = Path(dataset.source_file.path)

        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, sheet_name=sheet.name)
        elif file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        # Apply transforms to each mapped column
        for mapping in mappings:
            if not mapping.transforms:
                continue

            source_col = mapping.header_name

            if source_col not in df.columns:
                continue

            # Get transforms ordered by order field
            transforms = sorted(mapping.transforms, key=lambda t: t.order)

            # Apply transform chain to each value in column
            cleaned_values = []
            for value in df[source_col]:
                cleaned_value = value
                for transform in transforms:
                    cleaned_value = self.transform_service.apply_transform(
                        cleaned_value,
                        transform.fn,
                        transform.params or {}
                    )
                cleaned_values.append(cleaned_value)

            # Replace column with cleaned values
            df[source_col] = cleaned_values

        # Keep only mapped columns
        mapped_columns = [m.header_name for m in mappings if m.header_name in df.columns]
        return df[mapped_columns]

    def _generate_yaml_mapping(
        self,
        model: str,
        mappings: List[Mapping],
        id_pattern: str
    ) -> Dict[str, Any]:
        """
        Generate YAML mapping configuration from database mappings.

        IMPORTANT: Does NOT include transforms since they're already applied to CSV!
        """
        # Detect unique key from column profiles
        unique_keys = self._detect_unique_keys(mappings)

        yaml_config = {
            'model': model,
            'id': id_pattern,
            'unique_key': unique_keys,
            'fields': {}
        }

        for mapping in mappings:
            if not mapping.target_field:
                continue

            target_field = mapping.target_field

            # Simple source mapping - NO transforms (already applied to CSV!)
            yaml_config['fields'][target_field] = {
                'source': mapping.header_name
            }

        return yaml_config

    def _detect_unique_keys(self, mappings: List[Mapping]) -> List[str]:
        """Detect which fields should be used as unique keys."""
        unique_keys = []

        for mapping in mappings:
            field_name = mapping.target_field

            # Check if field name suggests it's a unique key
            if field_name and any(keyword in field_name.lower()
                                for keyword in ['ref', 'code', 'external_id', 'key']):
                unique_keys.append(field_name)

        return unique_keys if unique_keys else []

    def _generate_id_patterns(
        self,
        dataset: Dataset,
        mappings_by_model: Dict[str, List[Mapping]]
    ) -> Dict[str, str]:
        """
        Generate external ID patterns for each model.

        Strategy:
        1. Look for fields like 'ref', 'code', 'customer_id'
        2. Check column profiles for low null%, high distinct%
        3. Generate pattern like "migr.partner.{ref}"
        4. Fallback to "migr.{model}.{_index}"
        """
        id_patterns = {}

        for model, mappings in mappings_by_model.items():
            # Find candidate key field
            candidate_key = None

            for mapping in mappings:
                field_name = mapping.target_field

                if field_name and any(keyword in field_name.lower()
                                    for keyword in ['ref', 'code', 'external_id']):
                    candidate_key = field_name
                    break

            # Generate pattern
            if candidate_key:
                # Clean model name for namespace (e.g., "res.partner" -> "partner")
                model_short = model.split('.')[-1]
                id_patterns[model] = f"migr.{model_short}.{{{candidate_key}}}"
            else:
                # Fallback to index-based
                model_short = model.split('.')[-1]
                id_patterns[model] = f"migr.{model_short}.{{_index}}"

        return id_patterns

    def _generate_lookup_tables(self, dataset: Dataset) -> Dict[str, pd.DataFrame]:
        """
        Generate lookup tables for many2many relationships.

        Returns dict of {table_name: dataframe}
        """
        # For now, return empty dict
        # TODO: Implement if Relationship model has many2many configs
        return {}

    def _generate_project_config(self) -> Dict[str, Any]:
        """Generate project.yml configuration."""
        return {
            'namespace': 'migr',
            'odoo_version': '16.0',
            'timezone': 'America/Chicago',
            'company': 'Generated by data-migrator',
            'environment': 'production',
            'strict_mode': False
        }

    def _group_mappings_by_model(self, dataset: Dataset) -> Dict[str, List[Mapping]]:
        """Group all chosen mappings by target Odoo model."""
        mappings_by_model = defaultdict(list)

        for sheet in dataset.sheets:
            for mapping in sheet.mappings:
                if mapping.chosen and mapping.target_model:
                    mappings_by_model[mapping.target_model].append(mapping)

        return dict(mappings_by_model)
