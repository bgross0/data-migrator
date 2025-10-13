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

        if not dataset.cleaned_file_path or not Path(dataset.cleaned_file_path).exists():
            raise ValueError(f"Dataset {dataset_id} has no cleaned data. Run profiling first.")

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
            # 1. Load cleaned data
            data = self._load_cleaned_data(dataset.cleaned_file_path)

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

    def _load_cleaned_data(self, cleaned_file_path: str) -> Dict[str, pl.DataFrame]:
        """
        Load cleaned data from file using Polars.

        Returns:
            Dict of {sheet_name: DataFrame}
        """
        file_path = Path(cleaned_file_path)

        if file_path.suffix.lower() in ['.csv', '.cleaned.csv']:
            return {'Sheet1': pl.read_csv(file_path)}
        else:
            # Read all sheets from Excel
            return pl.read_excel(file_path, sheet_id=None)

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
                # Apply transformations based on mapping type
                for mapping in model_mapping_list:
                    if mapping.mapping_type == "lambda" and mapping.lambda_function:
                        # Apply lambda transformation
                        df = self.lambda_transformer.apply_lambda_mapping(
                            df,
                            mapping.target_field,
                            mapping.lambda_function
                        )
                    elif mapping.mapping_type == "direct":
                        # Simple column rename for direct mappings
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
