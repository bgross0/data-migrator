"""
Export API endpoints for converting datasets to external formats.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.odoo_migrate_export import OdooMigrateExportService
from app.services.export_service import ExportService, ExportResult
from app.services.graph_execute_service import GraphExecuteService
from app.schemas.export import ExportResponse
from app.models.graph import GraphRun

router = APIRouter()


@router.post("/datasets/{dataset_id}/export/odoo-migrate")
async def export_to_odoo_migrate(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """
    Export dataset to odoo-migrate format.

    This endpoint transforms data-migrator's interactive cleanup work
    into odoo-migrate's deterministic file-based pipeline format.

    Returns ZIP file containing:
    - config/mappings/*.yml - Field mappings WITHOUT transforms (already applied)
    - config/lookups/*.csv - Lookup tables for many2many relationships
    - config/ids.yml - External ID patterns
    - config/project.yml - Project configuration
    - data/raw/*.csv - CLEANED CSV files with transforms already applied

    The exported files can be used directly with odoo-migrate CLI:
    1. Extract ZIP to odoo-migrate directory
    2. Run: odoo-migrate source prepare
    3. Run: odoo-migrate transform execute config/mappings/*.yml
    4. Run: odoo-migrate validate check
    5. Run: odoo-migrate load run RUN_ID --url ... --db ... --username ... --password ...
    """
    try:
        service = OdooMigrateExportService(db)
        zip_bytes = await service.export_dataset(dataset_id)

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=dataset_{dataset_id}_odoo_migrate.zip"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/datasets/{dataset_id}/export/odoo-migrate/preview")
async def preview_export(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """
    Preview what will be exported without generating the full ZIP.

    Returns metadata about the export:
    - List of models that will be exported
    - Number of mappings per model
    - Detected external ID patterns
    - Number of lookup tables
    """
    try:
        service = OdooMigrateExportService(db)
        dataset = service._load_dataset_with_relations(dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Group mappings by model
        mappings_by_model = service._group_mappings_by_model(dataset)

        # Generate ID patterns
        id_patterns = service._generate_id_patterns(dataset, mappings_by_model)

        # Build preview response
        models_info = []
        for model, mappings in mappings_by_model.items():
            models_info.append({
                "model": model,
                "field_count": len(mappings),
                "external_id_pattern": id_patterns.get(model),
                "fields": [
                    {
                        "source": m.header_name,
                        "target": m.target_field,
                        "has_transforms": len(m.transforms) > 0
                    }
                    for m in mappings if m.target_field
                ]
            })

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "models": models_info,
            "total_models": len(models_info),
            "namespace": "migr"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/datasets/{dataset_id}/export-for-odoo", response_model=ExportResponse)
def export_for_odoo(
    dataset_id: int,
    graph_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Export dataset to deterministic Odoo CSV format.

    OPTIONS:
    - Legacy mode: Fixed registry-based export (if graph_id is None)
    - Graph mode: Execute using graph-driven workflow (if graph_id is provided)

    Legacy Mode:
    1. Validates data against registry specs
    2. Tracks exceptions (bad rows never block good rows)
    3. Generates deterministic external IDs with dedup tracking
    4. Applies idempotent normalizations (phone, email, date)
    5. Emits CSVs in correct import order (parents before children)
    6. Returns ZIP with all CSVs + exception summary

    Graph Mode:
    1. Execute nodes topologically with real-time progress
    2. Handle failures gracefully (continue on node failures)
    3. Skip problematic nodes but complete remaining pipeline
    4. Real-time progress tracking per node
    5. Node-level validation and error handling

    Returns:
    - ZIP file path with CSVs ready for Odoo import
    - Per-model counts (rows emitted, exceptions)
    - Exception summary by error code
    - Execution progress tracking
    """
    try:
        # Check if graph_id provided for graph-driven execution
        if graph_id is not None:
            # Use new graph-driven execution
            service = GraphExecuteService(db)
            result = service.execute_graph_export(dataset_id, graph_id)
        else:
            # Use legacy export service
            service = ExportService(db)
            result = service.export_to_odoo_csv(dataset_id)

        # Convert to ExportResponse format
        if isinstance(result, ExportResult):
            models = result.models
            total_emitted = result.total_emitted
            total_exceptions = result.total_exceptions
        else:
            # Handle case where service returns RunResponse
            run = None
            if hasattr(result, 'id'):
                run = db.query(GraphRun).filter(GraphRun.id == result.id).first()
            
            models = []
            if run and run.metadata:
                for model_name in run.metadata.get("executed_models", []):
                    model_summary = {
                        "model": model_name,
                        "csv_filename": f"{model_name}.csv",
                        "rows_emitted": run.metadata.get(f"{model_name}_rows_emitted", 0),
                        "exceptions_count": run.metadata.get(f"{model_name}_exceptions_count", 0)
                    }
                    models.append(model_summary)
                
            total_emitted = run.metadata.get("total_emitted", 0) if run else 0
            total_exceptions = len(run.metadata.get("failed_nodes", [])) if run else 0
            error_message = run.error_message if run else None
        
        return ExportResponse(
            dataset_id=dataset_id, 
            zip_path=result.zip_path if hasattr(result, 'zip_path') else "",
            models=models,
            total_emitted=total_emitted,
            total_exceptions=total_exceptions,
            exceptions_by_code=result.exceptions_by_code if hasattr(result, 'exceptions_by_code') else {},
            message=error_message or "Export completed",
            current_node=run.current_node if run else None,
            progress=run.progress if run else 0,
            metadata=run.metadata or {}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
