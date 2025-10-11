from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.dataset_service import DatasetService
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetListResponse
from app.field_mapper.core.module_registry import get_module_registry

router = APIRouter()


@router.post("/datasets/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = None,
    db: Session = Depends(get_db),
):
    """Upload a spreadsheet file and create a dataset."""
    service = DatasetService(db)
    dataset = await service.create_from_upload(file, name)
    return dataset


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all datasets."""
    service = DatasetService(db)
    datasets = service.list_datasets(skip=skip, limit=limit)
    return {"datasets": datasets, "total": len(datasets)}


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Get a specific dataset by ID."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Delete a dataset and all associated data."""
    service = DatasetService(db)
    success = service.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"status": "deleted"}


@router.get("/modules")
async def get_available_modules():
    """Get all available Odoo module groups for selection."""
    registry = get_module_registry()
    groups = registry.get_all_groups()

    return {
        "modules": [
            {
                "name": g.name,
                "display_name": g.display_name,
                "description": g.description,
                "icon": g.icon,
                "model_count": len(g.models),
                "priority": g.priority
            }
            for g in groups
        ]
    }


@router.post("/datasets/{dataset_id}/modules")
async def set_dataset_modules(
    dataset_id: int,
    modules: List[str],
    db: Session = Depends(get_db)
):
    """Set selected modules for a dataset to improve field mapping accuracy."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Validate module names
    registry = get_module_registry()
    valid_modules = {g.name for g in registry.get_all_groups()}
    invalid_modules = set(modules) - valid_modules

    if invalid_modules:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid module names: {list(invalid_modules)}"
        )

    # Update dataset
    dataset.selected_modules = modules
    db.commit()

    # Calculate how many models this reduces to
    selected_models = registry.get_models_for_groups(modules)

    return {
        "dataset_id": dataset_id,
        "selected_modules": modules,
        "model_count": len(selected_models),
        "models": list(selected_models)[:20]  # Show first 20 models
    }


@router.get("/datasets/{dataset_id}/modules")
async def get_dataset_modules(dataset_id: int, db: Session = Depends(get_db)):
    """Get selected modules for a dataset."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    registry = get_module_registry()
    selected_models = []

    if dataset.selected_modules:
        selected_models = list(registry.get_models_for_groups(dataset.selected_modules))

    return {
        "dataset_id": dataset_id,
        "selected_modules": dataset.selected_modules or [],
        "detected_domain": dataset.detected_domain,
        "model_count": len(selected_models),
        "models": selected_models[:20]  # Show first 20 models
    }


@router.post("/datasets/{dataset_id}/suggest-modules")
async def suggest_modules_for_dataset(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Suggest appropriate modules based on dataset columns."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get column names from all sheets
    column_names = []
    for sheet in dataset.sheets:
        for profile in sheet.column_profiles:
            column_names.append(profile.column_name)

    # Get suggestions
    registry = get_module_registry()
    suggested = registry.suggest_groups_for_columns(column_names)

    return {
        "dataset_id": dataset_id,
        "suggested_modules": suggested,
        "column_count": len(column_names),
        "analyzed_columns": column_names[:10]  # Show first 10 columns
    }
