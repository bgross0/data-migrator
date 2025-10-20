"""
Graph execution service for running graph-based export pipelines.

Executes nodes in topological order with real-time progress tracking
and handles failures gracefully.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import polars as pl

from app.models.graph import Graph, GraphRun
from app.schemas.run import RunResponse, GraphExecutionPlan
from app.schemas.graph import GraphSpec
from app.services.graph_service import GraphService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.registry.loader import RegistryLoader


class GraphExecuteService:
    """Service for executing graph-based export pipelines."""
    
    def __init__(self, db: Session):
        """
        Initialize execution service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.export_service = ExportService(db)
        self.graph_service = GraphService(db)
        self.import_service = ImportService(db)

        # Use absolute path to registry
        from pathlib import Path
        registry_path = Path(__file__).parent.parent.parent / "registry" / "odoo.yaml"
        self.registry_loader = RegistryLoader(registry_path)

    def create_execution_plan(self, graph_spec: GraphSpec) -> GraphExecutionPlan:
        """
        Analyze graph and create execution plan.
        
        Args:
            graph_spec: GraphSpec to analyze
            
        Returns:
            GraphExecutionPlan with execution order and metadata
        """
        registry = self.registry_loader.load()
        
        # Extract model nodes in graph
        model_nodes = [n for n in graph_spec.nodes if n.data and n.data.odooModel]
        model_names = [n.data.odooModel for n in model_nodes]
        
        # Validate all models exist in registry
        for node in model_nodes:
            if node.data.odooModel not in registry.models:
                raise ValueError(f"Model '{node.data.odooModel}' not found in registry")
        
        # Get topological execution order that respects dependencies
        execution_order = []
        processed = set()
        
        def get_dependencies(model_name: str) -> List[str]:
            """Get unprocessed dependencies for a model."""
            if model_name in processed:
                return []
            model_spec = registry.models[model_name]
            deps = []
            for field_spec in model_spec.fields.values():
                if field_spec.type == "m2o" and field_spec.target:
                    if field_spec.target in registry.models:
                        deps.append(field_spec.target)
            return deps
        
        # Topological sort
        while len(execution_order) < len(model_names):
            for model_name in model_names:
                if model_name in processed:
                    continue
                deps = get_dependencies(model_name)
                # All dependencies processed, add to execution order
                if all(dep in processed for dep in deps):
                    execution_order.append(model_name)
                    processed.add(model_name)
        
        # Add metadata
        return GraphExecutionPlan(
            execution_order=execution_order,
            phases=[
                {
                    "name": "Base Models",
                    "models": execution_order[:4],
                    "description": "Core infrastructure and reference data"
                },
                {
                    "name": "Business Models", 
                    "models": execution_order[4:10],
                    "description": "Core business entities"
                },
                {
                    "name": "Advanced Models",
                    "models": execution_order[10:],
                    "description": "Specialized workflows and analytics"
                }
            ],
            estimated_duration_minutes=len(model_names) * 2,  # Rough estimate
            requirements=[
                "All models must exist in registry",
                "Dataset must contain required columns",
                "Connectivity to Odoo for final import"
            ]
        )

    def create_graph_run(self, dataset_id: int, graph_id: int, dry_run: bool = False) -> RunResponse:
        """
        Create and initialize a graph execution run.
        
        Args:
            dataset_id: ID of dataset to export
            graph_id: ID of graph to execute
            dry_run: If True, validate only (no actual export)
            
        Returns:
            RunResponse with run details
        """
        graph = self.graph_service.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
            
        run = self.graph_service.create_run(graph_id, dataset_id)
        
        return RunResponse(
            id=run.id,
            dataset_id=run.dataset_id,
            graph_id=run.graph_id,
            status="queued",
            started_at=run.started_at.isoformat(),
            metadata={
                "dry_run": dry_run,
                "graph_name": graph.name
            }
        )

    def execute_graph_export(self, dataset_id: int, graph_id: int, run_id: Optional[str] = None) -> RunResponse:
        """
        Execute graph-driven export pipeline.

        Follows graph topology with real-time progress tracking.
        Handles failures gracefully and continues with remaining nodes.

        Args:
            dataset_id: ID of dataset to export
            graph_id: ID of graph defining export workflow
            run_id: Optional existing run ID to update (for concurrent safety)

        Returns:
            RunResponse with final statistics
        """
        graph = self.graph_service.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")

        from app.schemas.graph import GraphSpec
        graph_spec = GraphSpec(**graph.spec)

        # Use provided run_id or create new run
        if run_id:
            run = self.graph_service.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            run_response = RunResponse(
                id=run.id,
                dataset_id=run.dataset_id,
                graph_id=run.graph_id,
                status=run.status,
                started_at=run.started_at.isoformat() if run.started_at else None,
                metadata=run.context or {}
            )
        else:
            # Create new run if not provided
            run_response = self.create_graph_run(dataset_id, graph_id)
        
        try:
            # Plan execution
            plan = self.create_execution_plan(graph_spec)
            
            # Initialize execution state
            executed_nodes: List[str] = []
            failed_nodes: List[str] = []
            total_steps = len(plan.execution_order) if plan.execution_order else 1
            total_emitted = 0

            # Update status with initial context
            self.graph_service.update_run_status(
                run_response.id,
                status="running",
                context={
                    "dataset_id": dataset_id,
                    "graph_id": graph_id,
                    "plan": plan.execution_order,
                    "total_steps": total_steps
                }
            )

            # Log execution start
            self.graph_service.append_log(
                run_response.id,
                f"Starting graph execution with {total_steps} models",
                "info"
            )

            # Execute nodes in dependency order
            for i, model_name in enumerate(plan.execution_order):
                try:
                    # Update progress
                    progress = int(((i + 1) / total_steps) * 100)
                    self.graph_service.update_run_status(
                        run_response.id,
                        status="running",
                        progress=progress,
                        current_node=f"model_{model_name}",
                    )
                    
                    # Execute node (model export)
                    result = self.execute_model_node(
                        model_name, run_response.id, dataset_id
                    )
                    
                    if result["success"]:
                        executed_nodes.append(model_name)
                        total_emitted += result["rows_emitted"]
                        
                        # Log success
                        self._log_info(
                            run_response.id, 
                            f"✅ Exported {model_name}: {result['rows_emitted']} rows"
                        )
                    else:
                        failed_nodes.append(model_name)
                        self._log_error(
                            run_response.id,
                            f"❌ Failed to export {model_name}: {result['error']}"
                        )
                        if not self._can_continue_execution(plan, executed_nodes, failed_nodes):
                            break  # Too many failures, stop execution                            
                except Exception as e:
                    failed_nodes.append(model_name)
                    self._log_error(
                        run_response.id,
                        f"💥 Unexpected error in {model_name}: {str(e)}"
                    )
                    if not self._can_continue_execution(plan, executed_nodes, failed_nodes):
                        break  # Too many failures, stop execution
                        
            # Final status
            status = "completed" if len(failed_nodes) == 0 else "partial"
            message = f"Completed {len(executed_nodes)}/{len(plan.execution_order)} models"
            
            if len(failed_nodes) > 0:
                message += f" (failed: {', '.join(failed_nodes)})"
            
            self.graph_service.update_run_status(
                run_response.id,
                status=status,
                progress=100,
                finished_at=datetime.utcnow(),
                error_message=message if status != "completed" else None,
                context={
                    "executed_nodes": executed_nodes,
                    "failed_nodes": failed_nodes,
                    "total_emitted": total_emitted,
                },
            )
            
            # Refresh run data for response
            updated_run = self.graph_service.get_run(run_response.id)
            
            return RunResponse(
                id=updated_run.id,
                dataset_id=updated_run.dataset_id,
                graph_id=updated_run.graph_id,
                status=status,
                progress=100,
                error_message=message if status != "completed" else None,
                metadata=updated_run.context or {},
            )
            
        except Exception as e:
            # Final error handling
            self.graph_service.update_run_status(
                run_response.id,
                status="failed",
                error_message=f"Execution failed: {str(e)}",
                finished_at=datetime.utcnow(),
            )
            
            updated_run = self.graph_service.get_run(run_response.id)
            return RunResponse(
                id=updated_run.id,
                dataset_id=updated_run.dataset_id,
                graph_id=updated_run.graph_id,
                status="failed",
                progress=0,
                error_message=f"Execution failed: {str(e)}",
                metadata=updated_run.context or {},
            )

    def execute_model_node(self, model_name: str, run_id: int, dataset_id: int) -> Dict[str, Any]:
        """
        Execute a single model export node.

        Args:
            model_name: Odoo model name to export
            run_id: Run ID for logging
            dataset_id: Dataset ID for data access

        Returns:
            Dictionary with execution result
        """
        try:
            # Use existing export service logic for model export
            registry = self.registry_loader.load()

            if model_name not in registry.models:
                return {
                    "success": False,
                    "rows_emitted": 0,
                    "error": f"Model '{model_name}' not found in registry.",
                }

            model_spec = registry.models[model_name]

            # Get CONFIRMED mappings for this model
            from app.models.mapping import Mapping, MappingStatus
            mappings = self.db.query(Mapping).filter(
                Mapping.dataset_id == dataset_id,
                Mapping.target_model == model_name,
                Mapping.status == MappingStatus.CONFIRMED
            ).all()

            if not mappings:
                # No confirmed mappings for this model, skip
                return {"success": True, "rows_emitted": 0, "error": None}

            # Get dataset data for the sheet with mappings
            from app.adapters.repositories_sqlite import SQLiteDatasetsRepo
            datasets_repo = SQLiteDatasetsRepo(self.db)

            sheet_name = mappings[0].sheet.name if mappings[0].sheet else None
            df = datasets_repo.get_dataframe(dataset_id, sheet_name=sheet_name)

            if df is None or len(df) == 0:
                return {"success": True, "rows_emitted": 0, "error": None}

            # Add source_ptr if missing
            if "source_ptr" not in df.columns:
                df = df.with_columns(
                    pl.Series("source_ptr", [f"row_{i}" for i in range(len(df))])
                )

            # Apply mappings and transforms to prepare data for the target model
            df = self.export_service._apply_mappings_and_transforms(df, mappings, model_spec)

            # Use existing validation and emission logic
            from app.validate.validator import Validator
            from app.export.csv_emitter import CSVEmitter
            from app.adapters.repositories_sqlite import SQLiteExceptionsRepo

            validation_repo = SQLiteExceptionsRepo(self.db)
            fk_cache: Dict[str, set] = {}  # Empty cache for each run

            # Create output directory first
            output_dir = self.export_service.artifact_root / str(dataset_id)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize CSVEmitter with proper output directory
            csv_emitter = CSVEmitter(registry, validation_repo, dataset_id, output_dir)

            validator = Validator(validation_repo, fk_cache, dataset_id)
            validation_result = validator.validate(df, model_spec, registry.seeds)

            # Commit exceptions
            self.db.commit()

            # Use CSV emitter for deterministic generation
            if len(validation_result.valid_df) > 0:
                from app.export.idgen import reset_dedup_tracker
                reset_dedup_tracker()
                
                # Emit to temporary location
                csv_path, emitted_ids = csv_emitter.emit(
                    validation_result.valid_df, model_name
                )
                
                return {
                    "success": True,
                    "rows_emitted": len(validation_result.valid_df),
                    "csv_path": str(csv_path),
                    "error": None,
                }
            else:
                return {
                    "success": True,
                    "rows_emitted": 0,
                    "error": None,
                }
                
        except Exception as e:
            return {
                "success": False,
                "rows_emitted": 0,
                "error": str(e),
            }

    def _can_continue_execution(self, plan: GraphExecutionPlan, executed_nodes: List[str], failed_nodes: List[str]) -> bool:
        """Determine if execution should continue given failures."""
        total_models = len(plan.execution_order)

        # Allow up to 50% failures before stopping
        return len(failed_nodes) < (total_models * 0.5)

    def _log_info(self, run_id: str, message: str) -> None:
        """Log info message for run."""
        from app.models.graph import GraphRun
        db = self.db

        run = db.query(GraphRun).filter(GraphRun.id == run_id).first()
        if run:
            logs = run.logs or []
            logs.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "info",
                    "message": message,
                }
            )
            run.logs = logs
            self.db.commit()

    def _log_error(self, run_id: str, message: str) -> None:
        """Log error message for run."""
        from app.models.graph import GraphRun
        db = self.db

        run = db.query(GraphRun).filter(GraphRun.id == run_id).first()
        if run:
            logs = run.logs or []
            logs.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "error",
                    "message": message,
                }
            )
            run.logs = logs
            self.db.commit()
