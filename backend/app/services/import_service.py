from sqlalchemy.orm import Session
from app.models import Run, Dataset, Mapping
from app.schemas.run import RunCreate
from app.models.run import RunStatus
from app.connectors.odoo import OdooConnector
from app.importers.executor import TwoPhaseImporter
from app.importers.graph import ImportGraph as GraphBuilder
from app.core.lambda_transformer import LambdaTransformer
from pathlib import Path
from typing import Dict, List, Any
import polars as pl
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ImportService:
    def __init__(self, db: Session):
        self.db = db
        self.lambda_transformer = LambdaTransformer()

    async def create_run(self, dataset_id: int, run_data: RunCreate):
        """Create a new import run."""
        run = Run(
            dataset_id=dataset_id,
            graph_id=run_data.graph_id,
            status=RunStatus.PENDING,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        # TODO: Trigger import task asynchronously
        # from app.services.import_tasks import execute_import
        # execute_import.delay(run.id, dry_run=run_data.dry_run)

        return run

    def execute_import(self, dataset_id: int, odoo: OdooConnector, dry_run: bool = False) -> Run:
        """
        Execute import for a dataset.

        Args:
            dataset_id: ID of dataset to import
            odoo: OdooConnector instance
            dry_run: If True, validate but don't write to Odoo

        Returns:
            Run object with import stats
        """
        # Get dataset with all relationships
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Determine which file to use (prefer cleaned, fall back to raw)
        if dataset.cleaned_file_path and Path(dataset.cleaned_file_path).exists():
            data_file_path = dataset.cleaned_file_path
            logger.info(f"Using cleaned data from {data_file_path}")
        elif dataset.source_file and dataset.source_file.path:
            data_file_path = dataset.source_file.path
            logger.warning(f"No cleaned data available, falling back to raw data from {data_file_path}")
        else:
            raise ValueError(f"Dataset {dataset_id} has no data file available.")

        # Get confirmed mappings
        mappings = self.db.query(Mapping).filter(
            Mapping.dataset_id == dataset_id,
            Mapping.chosen == True
        ).all()

        if not mappings:
            raise ValueError(f"Dataset {dataset_id} has no confirmed mappings. Please confirm mappings first.")

        # Create run
        run = Run(
            dataset_id=dataset_id,
            status=RunStatus.IMPORTING,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            # 1. Load data (cleaned or raw)
            data = self._load_data(data_file_path)

            # 2. Apply mappings to transform data
            mapped_data = self._apply_mappings(data, mappings)

            # 3. Build import graph from mapped models
            graph = self._build_graph(mappings)

            # 4. Execute import via TwoPhaseImporter
            importer = TwoPhaseImporter(self.db, odoo, run)
            stats = importer.execute(graph, mapped_data)

            # 5. Update run with results
            run.status = RunStatus.COMPLETED
            run.stats = stats
            self.db.commit()

            return run

        except Exception as e:
            run.status = RunStatus.FAILED
            run.stats = {"error": str(e)}
            self.db.commit()
            raise

    def _load_data(self, file_path_str: str) -> Dict[str, pl.DataFrame]:
        """
        Load data from file using Polars (works with both cleaned and raw files).

        Returns:
            Dict of {sheet_name: DataFrame}
        """
        file_path = Path(file_path_str)

        if file_path.suffix.lower() in ['.csv', '.cleaned.csv'] or '.csv' in file_path.name:
            return {'Sheet1': pl.read_csv(file_path)}
        elif file_path.suffix.lower() in ['.xlsx', '.xls'] or '.xlsx' in file_path.name or '.xls' in file_path.name:
            # Read all sheets from Excel
            try:
                return pl.read_excel(file_path, sheet_id=None)
            except Exception as e:
                # Fallback to pandas if Polars fails
                logger.warning(f"Polars Excel read failed, trying pandas: {e}")
                import pandas as pd
                excel_file = pd.ExcelFile(file_path)
                result = {}
                for sheet_name in excel_file.sheet_names:
                    df_pandas = pd.read_excel(excel_file, sheet_name=sheet_name)
                    result[sheet_name] = pl.from_pandas(df_pandas)
                return result
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def _apply_mappings(self, data: Dict[str, pl.DataFrame], mappings: List[Mapping]) -> Dict[str, List[Dict]]:
        """
        Apply mappings (including lambda transformations) to transform dataframes to Odoo records.

        Args:
            data: Dict of {sheet_name: DataFrame}
            mappings: List of confirmed Mapping objects

        Returns:
            Dict of {model_name: [records]}
        """
        # Group mappings by sheet and model
        sheet_mappings = defaultdict(list)
        for mapping in mappings:
            sheet_mappings[mapping.sheet_id].append(mapping)

        # Transform data
        model_records = defaultdict(list)

        for sheet_id, sheet_mappings_list in sheet_mappings.items():
            # Get sheet name and DataFrame
            sheet = sheet_mappings_list[0].dataset.sheets
            sheet_obj = next((s for s in sheet if s.id == sheet_id), None)
            if not sheet_obj:
                continue

            sheet_name = sheet_obj.name
            if sheet_name not in data:
                continue

            df = data[sheet_name]

            # Group mappings by target model
            model_mappings = defaultdict(list)
            for mapping in sheet_mappings_list:
                if mapping.target_model:
                    model_mappings[mapping.target_model].append(mapping)

            # Process each model's mappings
            for model, model_mapping_list in model_mappings.items():
                # Apply lambda mappings first to preserve original column names
                lambda_mappings = [
                    m for m in model_mapping_list if m.mapping_type == "lambda"
                ]
                direct_mappings = [
                    m for m in model_mapping_list if m.mapping_type != "lambda"
                ]

                for mapping in lambda_mappings:
                    missing_dependencies = [
                        dep for dep in (mapping.lambda_dependencies or []) if dep not in df.columns
                    ]
                    if missing_dependencies:
                        logger.warning(
                            "Skipping lambda mapping '%s.%s': missing dependencies %s",
                            model,
                            mapping.target_field,
                            ", ".join(missing_dependencies),
                        )
                        continue

                    if not mapping.lambda_function:
                        logger.warning(
                            "Skipping lambda mapping '%s.%s': lambda_function not set",
                            model,
                            mapping.target_field,
                        )
                        continue

                    df = self.lambda_transformer.apply_lambda_mapping(
                        df,
                        mapping.target_field,
                        mapping.lambda_function,
                        getattr(mapping, "data_type", None),
                    )

                # Apply direct mappings (column renames)
                for mapping in direct_mappings:
                    if mapping.header_name in df.columns and mapping.target_field:
                        df = df.rename({mapping.header_name: mapping.target_field})

                # Convert Polars DataFrame to list of records
                records = df.to_dicts()

                # Filter out null values and add to model_records
                for record in records:
                    cleaned_record = {
                        k: v for k, v in record.items()
                        if v is not None and k in [m.target_field for m in model_mapping_list]
                    }
                    if cleaned_record:
                        model_records[model].append(cleaned_record)

        return dict(model_records)

    def _build_graph(self, mappings: List[Mapping]) -> List[str]:
        """
        Build import graph (topological order) from mappings.

        Args:
            mappings: List of confirmed Mapping objects

        Returns:
            List of model names in import order
        """
        # Get unique models from mappings
        models = list(set(m.target_model for m in mappings if m.target_model))

        # Use default graph for now (can be enhanced later)
        graph_builder = GraphBuilder.from_default()

        # Filter to only models present in mappings
        full_order = graph_builder.topological_sort()
        filtered_order = [m for m in full_order if m in models]

        # Add any models not in default graph at the end
        for model in models:
            if model not in filtered_order:
                filtered_order.append(model)

        return filtered_order

    def list_runs(self, skip: int = 0, limit: int = 100):
        """List all runs."""
        return self.db.query(Run).offset(skip).limit(limit).all()

    def get_run(self, run_id: int):
        """Get a run by ID."""
        return self.db.query(Run).filter(Run.id == run_id).first()

    async def rollback_run(self, run_id: int) -> bool:
        """Rollback an import run."""
        # TODO: Implement rollback logic
        # 1. Find all KeyMap entries for this run
        # 2. Delete/archive Odoo records
        # 3. Update run status to ROLLED_BACK
        return False
