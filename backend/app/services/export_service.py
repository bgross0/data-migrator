"""
Export service - orchestrates full export pipeline.

Pipeline:
1. Load registry
2. Clear old exceptions
3. For each model in import_order:
   a. Get DataFrame (cleaned or raw)
   b. Add source_ptr if missing (use row index)
   c. Apply mappings and transforms
   d. Validate → track exceptions, get valid rows
   e. Emit CSV → generate IDs, normalize, write
   f. Populate FK cache with emitted IDs
4. Create ZIP of all CSVs
5. Return: zip_path, counts, exception summary

FK cache: maintained in-memory, populated after parent emit, never reads files back.
"""
from pathlib import Path
from typing import Dict, Set, List, Tuple
from dataclasses import dataclass
import zipfile
from sqlalchemy.orm import Session
import polars as pl

from app.core.config import settings
from app.registry.loader import RegistryLoader, Registry
from app.adapters.repositories_sqlite import SQLiteExceptionsRepo, SQLiteDatasetsRepo
from app.validate.validator import Validator
from app.export.csv_emitter import CSVEmitter
from app.export.idgen import reset_dedup_tracker
from app.models.mapping import Mapping, MappingStatus


@dataclass
class ModelExportSummary:
    """Summary for a single model export."""

    model: str
    csv_filename: str
    rows_emitted: int
    exceptions_count: int


@dataclass
class ExportResult:
    """Result of full export pipeline."""

    dataset_id: int
    zip_path: str
    models: List[ModelExportSummary]
    total_emitted: int
    total_exceptions: int
    exceptions_by_code: Dict[str, int]


class ExportService:
    """
    Export service - orchestrates validate → emit → ZIP pipeline.

    Maintains in-memory FK cache, never reads emitted files back.
    """

    def __init__(self, db: Session):
        """
        Initialize export service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.registry_path = Path(settings.REGISTRY_FILE)
        self.artifact_root = Path(settings.ARTIFACT_ROOT)
        self.exceptions_repo = SQLiteExceptionsRepo(db)
        self.datasets_repo = SQLiteDatasetsRepo(db)

    def export_to_odoo_csv(self, dataset_id: int) -> ExportResult:
        """
        Export dataset to Odoo-compatible CSVs.

        Full pipeline with FK cache and exception tracking.

        Args:
            dataset_id: ID of dataset to export

        Returns:
            ExportResult with ZIP path, counts, and exception summary

        Raises:
            ValueError: If dataset not found or registry invalid
        """
        # 1. Load registry
        loader = RegistryLoader(self.registry_path)
        registry = loader.load()

        # 2. Clear old exceptions for this dataset
        self.exceptions_repo.clear(dataset_id)
        self.db.commit()

        # 3. Prepare output directory
        output_dir = self.artifact_root / str(dataset_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 4. Initialize FK cache and emitter
        fk_cache: Dict[str, Set[str]] = {}
        csv_emitter = CSVEmitter(registry, self.exceptions_repo, dataset_id, output_dir)

        # 5. Process each model in import order
        model_summaries: List[ModelExportSummary] = []
        total_emitted = 0
        exceptions_by_code: Dict[str, int] = {}

        for model_name in registry.import_order:
            if model_name not in registry.models:
                continue  # Model in order but not in registry

            model_spec = registry.models[model_name]

            # Get mappings for this model
            mappings = self.db.query(Mapping).filter(
                Mapping.dataset_id == dataset_id,
                Mapping.target_model == model_name,
                Mapping.status == MappingStatus.CONFIRMED
            ).all()

            if not mappings:
                # No mappings for this model, skip
                continue

            # Get DataFrame (cleaned or raw)
            try:
                # Get the sheet that has mappings for this model
                sheet_name = mappings[0].sheet.name if mappings[0].sheet else None
                df = self.datasets_repo.get_dataframe(dataset_id, sheet_name=sheet_name)
            except ValueError:
                # No data for this model, skip
                continue

            # Add source_ptr if missing (use row index as fallback)
            if "source_ptr" not in df.columns:
                df = df.with_columns(
                    pl.Series("source_ptr", [f"row_{i}" for i in range(len(df))])
                )

            # Apply mappings and transforms to prepare data for the target model
            df = self._apply_mappings_and_transforms(df, mappings, model_spec)

            # Validate
            validator = Validator(self.exceptions_repo, fk_cache, dataset_id)
            validation_result = validator.validate(df, model_spec, registry.seeds)

            # Commit exceptions
            self.db.commit()

            # Update exception counts
            for code, count in validation_result.exceptions_by_code.items():
                exceptions_by_code[code] = exceptions_by_code.get(code, 0) + count

            # Emit CSV (only valid rows)
            if len(validation_result.valid_df) > 0:
                reset_dedup_tracker()  # Reset for this model
                csv_path, emitted_ids = csv_emitter.emit(
                    validation_result.valid_df, model_name
                )

                # Populate FK cache for children
                fk_cache[model_name] = emitted_ids

                # Track summary
                model_summaries.append(
                    ModelExportSummary(
                        model=model_name,
                        csv_filename=model_spec.csv,
                        rows_emitted=len(validation_result.valid_df),
                        exceptions_count=validation_result.exception_count,
                    )
                )
                total_emitted += len(validation_result.valid_df)

        # 6. Create ZIP archive
        zip_path = output_dir / f"odoo_export_{dataset_id}.zip"
        self._create_zip(output_dir, zip_path, model_summaries)

        # 7. Return result
        return ExportResult(
            dataset_id=dataset_id,
            zip_path=str(zip_path),
            models=model_summaries,
            total_emitted=total_emitted,
            total_exceptions=sum(exceptions_by_code.values()),
            exceptions_by_code=exceptions_by_code,
        )

    # Graph-driven export methods
    def execute_graph_export(self, dataset_id: int, graph_id: int, dry_run: bool = False) -> ExportResult:
        """Execute export using graph-driven pipeline."""
        from app.services.graph_execute_service import GraphExecuteService
        
        graph_execute_service = GraphExecuteService(self.db)
        run_response = graph_execute_service.execute_graph_export(dataset_id, graph_id)
        
        # Convert RunResponse to ExportResult format for API compatibility
        run = self.graph_service.get_run(run_response.id)
        models = [
            ModelExportSummary(
                model=m.model,
                csv_filename=f"{m.model}.csv",
                rows_emitted=m.rows_emitted,
                exceptions_count=m.exceptions_count
            )
            for m in run.metadata["executed_models"] if "executed_models" in run.metadata
        ]
        
        return ExportResult(
            dataset_id=dataset_id,
            zip_path="",  # ZIP path in run metadata
            models=models,
            total_emitted=run.metadata.get("total_emitted", 0),
            total_exceptions=0 if run.status == "completed" else len(run.metadata.get("failed_nodes", [])),
            exceptions_by_code={},
            message=run.error_message or f"Completed export"
        )

    def _apply_mappings_and_transforms(
        self, df: pl.DataFrame, mappings: list, model_spec
    ) -> pl.DataFrame:
        """
        Apply confirmed mappings and transforms to prepare data for target model.

        Args:
            df: Source dataframe
            mappings: List of confirmed mappings for this model
            model_spec: Target model specification

        Returns:
            Transformed dataframe ready for validation
        """
        # Create a new dataframe with only mapped columns
        result_df = pl.DataFrame()

        for mapping in mappings:
            if mapping.status != MappingStatus.CONFIRMED:
                continue

            source_col = mapping.header_name
            target_field = mapping.target_field

            if source_col not in df.columns:
                continue

            # Get the column data
            col_data = df[source_col]

            # Apply lambda function if specified
            if mapping.mapping_type == "lambda" and mapping.lambda_function:
                try:
                    # Execute lambda function on the column
                    # Lambda should be like: "lambda x: x.upper()"
                    func = eval(mapping.lambda_function)
                    col_data = col_data.map_elements(func, return_dtype=pl.Utf8)
                except Exception as e:
                    # Log error and skip this mapping
                    continue

            # Apply transforms in order
            for transform in sorted(mapping.transforms, key=lambda t: t.order):
                from app.core.transformer import TransformRegistry
                registry = TransformRegistry()
                transform_fn = registry.get(transform.fn)
                if transform_fn:
                    try:
                        col_data = col_data.map_elements(
                            lambda x: transform_fn(x, **transform.params) if transform.params else transform_fn(x),
                            return_dtype=pl.Utf8
                        )
                    except Exception:
                        # Skip failed transform
                        pass

            # Rename to target field name
            col_data = col_data.alias(target_field)

            # Add to result dataframe
            if len(result_df) == 0:
                result_df = pl.DataFrame({target_field: col_data})
            else:
                result_df = result_df.with_columns(col_data)

        # Add any required fields with defaults if not mapped
        for field_name, field_spec in model_spec.fields.items():
            if field_name not in result_df.columns and field_spec.required:
                if field_spec.default is not None:
                    # Add column with default value
                    result_df = result_df.with_columns(
                        pl.lit(field_spec.default).alias(field_name)
                    )

        # Keep source_ptr for tracking
        if "source_ptr" in df.columns and "source_ptr" not in result_df.columns:
            result_df = result_df.with_columns(df["source_ptr"])

        return result_df

    def _create_zip(
        self, output_dir: Path, zip_path: Path, summaries: List[ModelExportSummary]
    ) -> None:
        """
        Create ZIP archive of CSV files.

        Args:
            output_dir: Directory containing CSVs
            zip_path: Path for output ZIP
            summaries: List of model summaries (for CSV filenames)
        """
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for summary in summaries:
                csv_file = output_dir / summary.csv_filename
                if csv_file.exists():
                    zf.write(csv_file, summary.csv_filename)
