from sqlalchemy.orm import Session, joinedload
from pathlib import Path
from typing import Dict, Any
import polars as pl
from app.models import Mapping, Dataset, Sheet, ColumnProfile, Suggestion, SourceFile
from app.schemas.mapping import MappingUpdate
from app.models.mapping import MappingStatus
from app.core.config import settings
from app.core.lambda_transformer import LambdaTransformer

# Import deterministic field mapper
try:
    from app.field_mapper.main import DeterministicFieldMapper
    DETERMINISTIC_MAPPER_AVAILABLE = True
except ImportError:
    DETERMINISTIC_MAPPER_AVAILABLE = False
    DeterministicFieldMapper = None

# Import hybrid matcher
try:
    from app.core.hybrid_matcher import HybridMatcher
    HYBRID_MATCHER_AVAILABLE = True
except ImportError:
    HYBRID_MATCHER_AVAILABLE = False
    HybridMatcher = None


class MappingService:
    def __init__(self, db: Session):
        self.db = db
        self.lambda_transformer = LambdaTransformer()

        # Initialize deterministic field mapper with odoo-dictionary
        self.deterministic_mapper = None
        if DETERMINISTIC_MAPPER_AVAILABLE:
            dictionary_path = Path(settings.ODOO_DICTIONARY_PATH)
            if dictionary_path.exists():
                try:
                    self.deterministic_mapper = DeterministicFieldMapper(dictionary_path)
                except Exception as e:
                    print(f"Warning: Could not initialize DeterministicFieldMapper: {e}")

        # Initialize hybrid matcher (best of both worlds)
        self.hybrid_matcher = None
        if HYBRID_MATCHER_AVAILABLE:
            dictionary_path = Path(settings.ODOO_DICTIONARY_PATH)
            if dictionary_path.exists():
                try:
                    self.hybrid_matcher = HybridMatcher(dictionary_path)
                    print(f"✓ Initialized HybridMatcher with knowledge base")
                except Exception as e:
                    print(f"Warning: Could not initialize HybridMatcher: {e}")

    def get_mappings_for_dataset(self, dataset_id: int):
        """Get all mappings for a dataset."""
        return self.db.query(Mapping)\
            .options(
                joinedload(Mapping.suggestions),
                joinedload(Mapping.transforms)
            )\
            .filter(Mapping.dataset_id == dataset_id)\
            .all()

    async def generate_mappings_v2(self, dataset_id: int, use_deterministic: bool = True):
        """
        Generate mapping suggestions using the DeterministicFieldMapper.

        This uses the actual odoo-dictionary files for comprehensive model coverage.
        Routes to HybridMatcher when use_deterministic=False.
        """
        # If caller requested non-deterministic matching, route to hybrid matcher
        if not use_deterministic:
            if self.hybrid_matcher:
                return await self.generate_mappings_hybrid(dataset_id)
            raise RuntimeError("Hybrid matcher requested but not configured.")

        if not self.deterministic_mapper:
            raise RuntimeError("Deterministic field mapper is not available.")

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

        # Get selected modules for this dataset
        selected_modules = dataset.selected_modules if hasattr(dataset, 'selected_modules') else None
        if selected_modules:
            print(f"🎯 Using selected modules for mapping: {selected_modules}")

        all_mappings = []

        # Process each sheet
        for sheet in dataset.sheets:
            # Prefer cleaned data over raw data
            if dataset.cleaned_file_path and Path(dataset.cleaned_file_path).exists():
                file_path = Path(dataset.cleaned_file_path)
                print(f"INFO: Using cleaned data from {file_path}")
            else:
                file_path = Path(dataset.source_file.path)
                print(f"INFO: Using raw data from {file_path} (no cleaned data available)")

            try:
                # Check file type by extension (cleaned files use .cleaned.csv or .cleaned.xlsx)
                file_ext = file_path.suffix.lower()
                is_excel = file_ext in ['.xlsx', '.xls'] or '.xlsx' in file_path.name or '.xls' in file_path.name
                is_csv = file_ext == '.csv' or '.csv' in file_path.name

                if is_excel:
                    # Try multiple Excel reading methods with fallbacks
                    try:
                        # First try: Use fastexcel (default, fastest)
                        df = pl.read_excel(file_path, sheet_name=sheet.name)
                    except ModuleNotFoundError as e:
                        if 'fastexcel' in str(e):
                            print(f"WARNING: fastexcel not available, trying openpyxl...")
                            try:
                                # Second try: Use openpyxl engine
                                df = pl.read_excel(file_path, sheet_name=sheet.name, engine="openpyxl")
                            except Exception as e2:
                                print(f"WARNING: openpyxl failed, using pandas fallback: {e2}")
                                # Third try: Use pandas and convert to Polars
                                import pandas as pd
                                pandas_df = pd.read_excel(file_path, sheet_name=sheet.name)
                                df = pl.from_pandas(pandas_df)
                        else:
                            raise
                elif is_csv:
                    df = pl.read_csv(file_path)
                else:
                    continue

                # Use deterministic field mapper (now supports Polars natively)
                # map_dataframe returns Dict[str, List[FieldMapping]]
                # Structure: {column_name: [FieldMapping, ...]}
                sheet_mappings = self.deterministic_mapper.map_dataframe(
                    df,
                    sheet_name=sheet.name,
                    selected_modules=selected_modules
                )

                print(f"INFO: Found {len(sheet_mappings)} columns with mappings for sheet '{sheet.name}'")

                # Create mapping records for each column
                for column_name, field_mappings in sheet_mappings.items():
                    if not field_mappings:
                        continue

                    # Get top suggestion
                    top_mapping = field_mappings[0]

                    # Auto-confirm high confidence mappings (≥0.7)
                    confidence_value = float(top_mapping.confidence) if top_mapping.confidence is not None else 0.0
                    auto_confirm = confidence_value >= 0.7

                    # Create mapping record
                    # Convert numpy types to Python native types to avoid SQLAlchemy issues
                    mapping = Mapping(
                        dataset_id=dataset_id,
                        sheet_id=sheet.id,
                        header_name=column_name,
                        target_model=top_mapping.target_model,
                        target_field=top_mapping.target_field,
                        confidence=confidence_value,
                        status=MappingStatus.CONFIRMED if auto_confirm else MappingStatus.PENDING,
                        chosen=auto_confirm,  # Auto-choose high confidence mappings
                        rationale=top_mapping.rationale,
                    )

                    if hasattr(top_mapping, "mapping_type"):
                        mapping.mapping_type = top_mapping.mapping_type or "direct"

                    if mapping.mapping_type == "lambda":
                        mapping.header_name = column_name or f"lambda_{top_mapping.target_field}"
                        if getattr(top_mapping, "lambda_function", None):
                            mapping.lambda_function = top_mapping.lambda_function
                        if getattr(top_mapping, "lambda_dependencies", None):
                            mapping.join_config = {
                                "lambda_dependencies": top_mapping.lambda_dependencies
                            }
                        if getattr(top_mapping, "data_type", None):
                            mapping.join_config = mapping.join_config or {}
                            mapping.join_config["data_type"] = top_mapping.data_type
                        if getattr(top_mapping, "lambda_dependencies", None):
                            deps = ", ".join(top_mapping.lambda_dependencies)
                            mapping.rationale = (
                                f"{mapping.rationale} (lambda dependencies: {deps})"
                                if mapping.rationale
                                else f"Lambda dependencies: {deps}"
                            )

                    self.db.add(mapping)
                    self.db.flush()

                    # Store all candidates as suggestions (Top 10 for two-tier system)
                    candidates = [
                        {
                            "model": fm.target_model,
                            "field": fm.target_field,
                            "confidence": float(fm.confidence) if fm.confidence is not None else 0.0,
                            "confidence_tier": getattr(fm, "confidence_tier", "medium"),
                            "method": fm.matching_strategy,
                            "rationale": fm.rationale
                        }
                        for fm in field_mappings[:10]  # Top 10 (increased from 5)
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

    async def generate_mappings_hybrid(self, dataset_id: int):
        """
        Generate mapping suggestions using the HybridMatcher.

        This combines:
        - BusinessContextAnalyzer (intelligent model detection)
        - OdooKnowledgeBase (authoritative field metadata)
        - Hardcoded patterns (deterministic, proven matches)

        Requires the HybridMatcher to be available.
        """
        if not self.hybrid_matcher:
            raise RuntimeError("Hybrid matcher is not available.")

        # Delete existing mappings for this dataset before generating new ones
        self.db.query(Mapping).filter(Mapping.dataset_id == dataset_id).delete()
        self.db.commit()

        # Get dataset with sheets
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return []

        # Get selected modules for this dataset
        selected_modules = dataset.selected_modules if hasattr(dataset, 'selected_modules') else None
        if selected_modules:
            print(f"🎯 Using selected modules for mapping: {selected_modules}")

        all_mappings = []

        # Process each sheet
        for sheet in dataset.sheets:
            # Get all column profiles for this sheet
            profiles = self.db.query(ColumnProfile).filter(
                ColumnProfile.sheet_id == sheet.id
            ).all()

            # Get all column names for model detection
            column_names = [p.name for p in profiles]

            print(f"Processing sheet '{sheet.name}' with {len(column_names)} columns using HybridMatcher")

            # Generate mapping for each column
            for profile in profiles:
                # Get suggestions from hybrid matcher with full context (including selected modules)
                candidates = self.hybrid_matcher.match(
                    header=profile.name,
                    sheet_name=sheet.name,
                    column_names=column_names,
                    selected_modules=selected_modules
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

        print(f"✓ Generated {len(all_mappings)} mappings using HybridMatcher")
        return all_mappings

    def create_lambda_mapping(self, dataset_id: int, sheet_id: int, target_field: str,
                            lambda_function: str, target_model: str) -> Mapping:
        """Create a lambda transformation mapping."""
        mapping = Mapping(
            dataset_id=dataset_id,
            sheet_id=sheet_id,
            header_name=f"lambda_{target_field}",  # Virtual column name
            target_model=target_model,
            target_field=target_field,
            confidence=1.0,  # Lambda mappings are always high confidence
            status=MappingStatus.CONFIRMED,
            chosen=True,
            mapping_type="lambda",
            lambda_function=lambda_function,
            rationale=f"Lambda transformation for {target_field}"
        )
        mapping.join_config = {
            "lambda_dependencies": [],
            "data_type": None,
        }
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

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

        # Support updating lambda mappings
        if hasattr(mapping_data, 'mapping_type') and mapping_data.mapping_type:
            mapping.mapping_type = mapping_data.mapping_type
        if hasattr(mapping_data, 'lambda_function') and mapping_data.lambda_function:
            mapping.lambda_function = mapping_data.lambda_function
        if hasattr(mapping_data, 'join_config') and mapping_data.join_config:
            mapping.join_config = mapping_data.join_config

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
