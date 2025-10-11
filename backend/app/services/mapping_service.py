from sqlalchemy.orm import Session, joinedload
from pathlib import Path
from typing import Optional
import pandas as pd
from app.models import Mapping, Dataset, Sheet, ColumnProfile, Suggestion, SourceFile
from app.schemas.mapping import MappingUpdate
from app.core.matcher import HeaderMatcher
from app.models.mapping import MappingStatus
from app.core.config import settings

# Import deterministic field mapper
try:
    from app.field_mapper.main import DeterministicFieldMapper
    DETERMINISTIC_MAPPER_AVAILABLE = True
except ImportError:
    DETERMINISTIC_MAPPER_AVAILABLE = False
    DeterministicFieldMapper = None


class MappingService:
    def __init__(self, db: Session):
        self.db = db

        # Initialize deterministic field mapper with odoo-dictionary
        self.deterministic_mapper = None
        if DETERMINISTIC_MAPPER_AVAILABLE:
            dictionary_path = Path(settings.ODOO_DICTIONARY_PATH)
            if dictionary_path.exists():
                try:
                    self.deterministic_mapper = DeterministicFieldMapper(dictionary_path)
                except Exception as e:
                    print(f"Warning: Could not initialize DeterministicFieldMapper: {e}")

    def get_mappings_for_dataset(self, dataset_id: int):
        """Get all mappings for a dataset."""
        return self.db.query(Mapping)\
            .options(
                joinedload(Mapping.suggestions),
                joinedload(Mapping.transforms)
            )\
            .filter(Mapping.dataset_id == dataset_id)\
            .all()

    async def generate_mappings(self, dataset_id: int):
        """Generate mapping suggestions for a dataset."""
        # Delete existing mappings for this dataset before generating new ones
        self.db.query(Mapping).filter(Mapping.dataset_id == dataset_id).delete()
        self.db.commit()

        # Get dataset with sheets
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return []

        all_mappings = []

        # Process each sheet
        for sheet in dataset.sheets:
            # Get all column profiles for this sheet
            profiles = self.db.query(ColumnProfile).filter(
                ColumnProfile.sheet_id == sheet.id
            ).all()

            # Get all column names for better model detection
            column_names = [p.name for p in profiles]

            # Initialize matcher (will auto-detect model based on sheet and columns)
            matcher = HeaderMatcher(target_model=None)

            # Generate mapping for each column
            for profile in profiles:
                # Get suggestions from matcher with full context
                candidates = matcher.match(
                    header=profile.name,
                    sheet_name=sheet.name,
                    column_names=column_names
                )

                # Create mapping record with top suggestion
                top_candidate = candidates[0] if candidates else None

                mapping = Mapping(
                    dataset_id=dataset_id,
                    sheet_id=sheet.id,
                    header_name=profile.name,
                    target_model=top_candidate["model"] if top_candidate else None,
                    target_field=top_candidate["field"] if top_candidate else None,
                    confidence=top_candidate["confidence"] if top_candidate else 0.0,
                    status=MappingStatus.PENDING,
                    chosen=False,
                    rationale=top_candidate["rationale"] if top_candidate else None,
                )
                self.db.add(mapping)
                self.db.flush()  # Get the mapping ID

                # Store all candidates as suggestions
                if candidates:
                    suggestion = Suggestion(
                        mapping_id=mapping.id,
                        candidates=candidates  # Store as JSON
                    )
                    self.db.add(suggestion)

                all_mappings.append(mapping)

            self.db.commit()

        return all_mappings

    async def generate_mappings_v2(self, dataset_id: int, use_deterministic: bool = True):
        """
        Generate mapping suggestions using the DeterministicFieldMapper.

        This uses the actual odoo-dictionary files instead of hardcoded mappings.
        Falls back to v1 (hardcoded) if deterministic mapper is not available.
        """
        # Fall back to v1 if deterministic mapper not available
        if not use_deterministic or not self.deterministic_mapper:
            return await self.generate_mappings(dataset_id)

        # Delete existing mappings for this dataset before generating new ones
        self.db.query(Mapping).filter(Mapping.dataset_id == dataset_id).delete()
        self.db.commit()

        # Get dataset with source file
        dataset = self.db.query(Dataset).options(
            joinedload(Dataset.source_file),
            joinedload(Dataset.sheets)
        ).filter(Dataset.id == dataset_id).first()

        if not dataset or not dataset.source_file:
            return []

        all_mappings = []

        # Process each sheet
        for sheet in dataset.sheets:
            # Read the source file for this sheet
            file_path = Path(dataset.source_file.path)

            try:
                if file_path.suffix.lower() in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path, sheet_name=sheet.name)
                elif file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    continue

                # Use deterministic field mapper
                # map_dataframe returns Dict[str, List[FieldMapping]]
                # Structure: {column_name: [FieldMapping, ...]}
                sheet_mappings = self.deterministic_mapper.map_dataframe(df, sheet_name=sheet.name)

                print(f"INFO: Found {len(sheet_mappings)} columns with mappings for sheet '{sheet.name}'")

                # Create mapping records for each column
                for column_name, field_mappings in sheet_mappings.items():
                    if not field_mappings:
                        continue

                    # Get top suggestion
                    top_mapping = field_mappings[0]

                    # Create mapping record
                    # Convert numpy types to Python native types to avoid SQLAlchemy issues
                    mapping = Mapping(
                        dataset_id=dataset_id,
                        sheet_id=sheet.id,
                        header_name=column_name,
                        target_model=top_mapping.target_model,
                        target_field=top_mapping.target_field,
                        confidence=float(top_mapping.confidence) if top_mapping.confidence is not None else 0.0,
                        status=MappingStatus.PENDING,
                        chosen=False,
                        rationale=top_mapping.rationale,
                    )
                    self.db.add(mapping)
                    self.db.flush()

                    # Store all candidates as suggestions
                    candidates = [
                        {
                            "model": fm.target_model,
                            "field": fm.target_field,
                            "confidence": float(fm.confidence) if fm.confidence is not None else 0.0,
                            "method": fm.matching_strategy,
                            "rationale": fm.rationale
                        }
                        for fm in field_mappings[:5]  # Top 5
                    ]

                    suggestion = Suggestion(
                        mapping_id=mapping.id,
                        candidates=candidates
                    )
                    self.db.add(suggestion)

                    all_mappings.append(mapping)

                self.db.commit()

            except Exception as e:
                import traceback
                print(f"ERROR: Failed to process sheet '{sheet.name}': {e}")
                print(f"ERROR: Traceback: {traceback.format_exc()}")
                continue

        return all_mappings

    def update_mapping(self, mapping_id: int, mapping_data: MappingUpdate):
        """Update a mapping."""
        mapping = self.db.query(Mapping).filter(Mapping.id == mapping_id).first()
        if not mapping:
            return None

        if mapping_data.target_model is not None:
            mapping.target_model = mapping_data.target_model
        if mapping_data.target_field is not None:
            mapping.target_field = mapping_data.target_field
        if mapping_data.status is not None:
            mapping.status = mapping_data.status
        if mapping_data.chosen is not None:
            mapping.chosen = mapping_data.chosen
        if mapping_data.custom_field_definition is not None:
            mapping.custom_field_definition = mapping_data.custom_field_definition.model_dump()

        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def delete_mapping(self, mapping_id: int) -> bool:
        """Delete a mapping."""
        mapping = self.db.query(Mapping).filter(Mapping.id == mapping_id).first()
        if not mapping:
            return False
        self.db.delete(mapping)
        self.db.commit()
        return True
