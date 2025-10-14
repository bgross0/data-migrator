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
import re
import yaml
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

import pandas as pd
import polars as pl
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

        Raises:
            ValueError: If dataset not found or validation fails
        """
        # Load dataset with all relationships
        dataset = self._load_dataset_with_relations(dataset_id)

        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Validate before export
        validation_errors = self._validate_dataset_for_export(dataset)
        if validation_errors:
            error_msg = "Export validation failed:\n" + "\n".join(f"- {e}" for e in validation_errors)
            raise ValueError(error_msg)

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
        dataset = self.db.query(Dataset)\
            .options(
                joinedload(Dataset.source_file),
                joinedload(Dataset.sheets)
                    .joinedload(Sheet.column_profiles),
                joinedload(Dataset.mappings)
                    .joinedload(Mapping.transforms),
            )\
            .filter(Dataset.id == dataset_id)\
            .first()
                    
        return dataset

    def _validate_dataset_for_export(self, dataset: Dataset) -> List[str]:
        """
        Validate dataset is ready for export.

        Returns list of validation errors (empty if valid).
        """
        errors = []
        warnings = []

        # Check source file exists
        if not dataset.source_file or not Path(dataset.source_file.path).exists():
            errors.append("Source file not found or inaccessible")

        # Check at least one sheet exists
        if not dataset.sheets:
            errors.append("No sheets found in dataset")

        # Check at least one chosen mapping exists
        has_chosen_mapping = False
        for sheet in dataset.sheets:
            for mapping in sheet.mappings:
                if mapping.chosen:
                    has_chosen_mapping = True

                    # Validate chosen mappings have required fields
                    if not mapping.target_model:
                        errors.append(f"Mapping '{mapping.header_name}' missing target_model")
                    if not mapping.target_field:
                        errors.append(f"Mapping '{mapping.header_name}' missing target_field")

                    # Check many2many fields (ending with /id) have split + map transforms
                    if mapping.target_field and mapping.target_field.endswith('/id'):
                        transforms = sorted(mapping.transforms, key=lambda t: t.order) if mapping.transforms else []
                        has_split = any(t.fn == 'split' for t in transforms)
                        has_map = any(t.fn == 'map' for t in transforms)

                        if not has_split:
                            warnings.append(
                                f"Many2many field '{mapping.header_name}' → '{mapping.target_field}' "
                                f"should have 'split' transform"
                            )
                        if not has_map:
                            warnings.append(
                                f"Many2many field '{mapping.header_name}' → '{mapping.target_field}' "
                                f"should have 'map' transform (lookup table won't be generated)"
                            )

        if not has_chosen_mapping:
            errors.append("No mappings marked as chosen - nothing to export")

        # Log warnings (not blocking)
        for warning in warnings:
            print(f"⚠️  Warning: {warning}")

        return errors

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
    ) -> pl.DataFrame:
        """
        Read source file and apply all configured transforms.

        Returns cleaned dataframe with transforms applied.
        """
        file_path = Path(dataset.source_file.path)
        df = self._read_source_sheet(file_path, sheet.name)

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
            column_values = df.get_column(source_col)
            for value in column_values.to_list():
                cleaned_value = value
                for transform in transforms:
                    cleaned_value = self.transform_service.apply_transform(
                        cleaned_value,
                        transform.fn,
                        transform.params or {}
                    )

                # If transform chain resulted in a list (e.g., split + map),
                # join it back to semicolon-separated string for CSV export
                if isinstance(cleaned_value, list):
                    cleaned_value = ";".join(str(v) for v in cleaned_value)

                cleaned_values.append(cleaned_value)

            # Replace column with cleaned values
            df = df.with_columns(pl.Series(source_col, cleaned_values))

        # Keep only mapped columns
        mapped_columns = [m.header_name for m in mappings if m.header_name in df.columns]
        return df.select(mapped_columns) if mapped_columns else df.select([])

    def _read_source_sheet(self, file_path: Path, sheet_name: str) -> pl.DataFrame:
        """
        Read a specific sheet or CSV source file into a Polars DataFrame.

        Falls back to pandas for legacy Excel formats or edge cases.
        """
        suffix = file_path.suffix.lower()

        if suffix in ['.csv', '.cleaned.csv']:
            return pl.read_csv(file_path)

        if suffix == '.xlsx':
            try:
                return pl.read_excel(file_path, sheet_name=sheet_name)
            except Exception:
                return self._read_excel_with_pandas(file_path, sheet_name)

        if suffix == '.xls':
            return self._read_excel_with_pandas(file_path, sheet_name)

        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    @staticmethod
    def _read_excel_with_pandas(file_path: Path, sheet_name: str) -> pl.DataFrame:
        """
        Helper to load Excel files with pandas and convert to Polars.
        """
        import pandas as pd  # Local import to keep pandas optional

        pandas_df = pd.read_excel(file_path, sheet_name=sheet_name)
        return pl.from_pandas(pandas_df)

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

        Detects fields with split + map transforms and creates lookup CSVs.

        Example:
        - Transform chain: ["split:;", "map:tags"]
        - Source value: "VIP;Wholesale;Premium"
        - Creates tags.csv:
          source_key,external_id
          VIP,migr.tag.VIP
          Wholesale,migr.tag.Wholesale
          Premium,migr.tag.Premium

        Returns dict of {table_name: dataframe}
        """
        lookup_data = defaultdict(set)  # {table_name: set of unique values}

        # Scan all mappings for split + map patterns
        for sheet in dataset.sheets:
            for mapping in sheet.mappings:
                if not mapping.chosen or not mapping.transforms:
                    continue

                # Get transforms ordered by order field
                transforms = sorted(mapping.transforms, key=lambda t: t.order)

                # Detect split + map pattern
                has_split = False
                split_delimiter = ';'
                map_table_name = None

                for transform in transforms:
                    if transform.fn == 'split':
                        has_split = True
                        # Extract delimiter from params or default to ';'
                        if transform.params and 'delimiter' in transform.params:
                            split_delimiter = transform.params['delimiter']

                    # Look for map with table name in params
                    if transform.fn.startswith('map') or transform.fn == 'lookup':
                        # Extract table name from params
                        if transform.params and 'table' in transform.params:
                            map_table_name = transform.params['table']

                # If we found a split + map pattern, extract unique values
                if has_split and map_table_name:
                    # Read source file and extract values from this column
                    file_path = Path(dataset.source_file.path)

                    try:
                        if file_path.suffix.lower() in ['.xlsx', '.xls']:
                            df = pd.read_excel(file_path, sheet_name=sheet.name)
                        elif file_path.suffix.lower() == '.csv':
                            df = pd.read_csv(file_path)
                        else:
                            continue

                        source_col = mapping.header_name
                        if source_col not in df.columns:
                            continue

                        # Split values and collect unique items
                        for value in df[source_col].dropna():
                            items = str(value).split(split_delimiter)
                            for item in items:
                                item = item.strip()
                                if item:
                                    lookup_data[map_table_name].add(item)

                    except Exception as e:
                        # Skip if file can't be read
                        print(f"Warning: Could not read source file for lookup table generation: {e}")
                        continue

        # Convert to dataframes
        lookup_tables = {}
        for table_name, values in lookup_data.items():
            # Generate external IDs for each unique value
            records = []
            for value in sorted(values):
                # Sanitize value for external ID (replace spaces/special chars with _)
                sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', value)
                external_id = f"migr.{table_name}.{sanitized}"

                records.append({
                    'source_key': value,
                    'external_id': external_id
                })

            if records:
                lookup_tables[table_name] = pd.DataFrame(records)

        return lookup_tables

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
