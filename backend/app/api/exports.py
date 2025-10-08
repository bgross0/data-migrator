"""
Export API endpoints for converting datasets to external formats.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.odoo_migrate_export import OdooMigrateExportService

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
