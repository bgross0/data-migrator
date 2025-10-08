from sqlalchemy.orm import Session
from app.models import Mapping, Dataset, Sheet, ColumnProfile, Suggestion
from app.schemas.mapping import MappingUpdate
from app.core.matcher import HeaderMatcher
from app.core.odoo_synonyms import get_model_from_sheet_name
from app.models.mapping import MappingStatus


class MappingService:
    def __init__(self, db: Session):
        self.db = db

    def get_mappings_for_dataset(self, dataset_id: int):
        """Get all mappings for a dataset."""
        return self.db.query(Mapping).filter(Mapping.dataset_id == dataset_id).all()

    async def generate_mappings(self, dataset_id: int):
        """Generate mapping suggestions for a dataset."""
        # Get dataset with sheets
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return []

        all_mappings = []

        # Process each sheet
        for sheet in dataset.sheets:
            # Detect target model from sheet name
            target_model = get_model_from_sheet_name(sheet.name)

            # Initialize matcher for this model
            matcher = HeaderMatcher(target_model=target_model)

            # Get column profiles for this sheet
            profiles = self.db.query(ColumnProfile).filter(
                ColumnProfile.sheet_id == sheet.id
            ).all()

            # Generate mapping for each column
            for profile in profiles:
                # Get suggestions from matcher
                candidates = matcher.match(profile.name, sheet_name=sheet.name)

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
