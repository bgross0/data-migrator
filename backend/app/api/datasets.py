from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.dataset_service import DatasetService
from app.services.mapping_service import MappingService
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetListResponse
from app.field_mapper.core.module_registry import get_module_registry
from pathlib import Path
import pandas as pd
import json

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


@router.get("/datasets/{dataset_id}/cleaning-report")
async def get_cleaning_report(dataset_id: int, db: Session = Depends(get_db)):
    """Get the data cleaning report for a dataset."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.cleaning_report:
        raise HTTPException(
            status_code=404,
            detail="No cleaning report available. Dataset may not have been profiled with cleaning enabled."
        )

    return {
        "dataset_id": dataset_id,
        "profiling_status": dataset.profiling_status,
        "cleaning_report": dataset.cleaning_report
    }


@router.get("/datasets/{dataset_id}/cleaned-data")
async def get_cleaned_data_preview(
    dataset_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Preview cleaned data from a dataset."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.cleaned_file_path or not Path(dataset.cleaned_file_path).exists():
        raise HTTPException(
            status_code=404,
            detail="No cleaned data available. Dataset may not have been profiled with cleaning enabled."
        )

    # Read cleaned data
    file_path = Path(dataset.cleaned_file_path)
    preview_data = {}

    try:
        if file_path.suffix.lower() in ['.csv', '.cleaned.csv']:
            df = pd.read_csv(file_path, nrows=limit)
            preview_data['Sheet1'] = {
                "columns": df.columns.tolist(),
                "data": df.to_dict('records'),
                "total_rows": len(df)
            }
        else:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=limit)
                preview_data[sheet_name] = {
                    "columns": df.columns.tolist(),
                    "data": df.to_dict('records'),
                    "total_rows": len(df)
                }

        return {
            "dataset_id": dataset_id,
            "cleaned_file_path": str(dataset.cleaned_file_path),
            "sheets": preview_data,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading cleaned data: {str(e)}"
        )


@router.get("/datasets/{dataset_id}/download-cleaned")
async def download_cleaned_data(dataset_id: int, db: Session = Depends(get_db)):
    """
    Download the cleaned data file.

    Returns the cleaned CSV/XLSX file that can be directly imported into Odoo.
    The file has already been cleaned and transformed during the profiling step.
    """
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.cleaned_file_path or not Path(dataset.cleaned_file_path).exists():
        raise HTTPException(
            status_code=404,
            detail="No cleaned data available. Dataset may not have been profiled with cleaning enabled."
        )

    file_path = Path(dataset.cleaned_file_path)

    # Generate a clean filename
    original_name = dataset.source_file.original_filename if dataset.source_file else "dataset"
    base_name = Path(original_name).stem
    extension = file_path.suffix
    filename = f"{base_name}_cleaned{extension}"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@router.get("/datasets/{dataset_id}/export-for-odoo")
async def export_for_odoo(dataset_id: int, db: Session = Depends(get_db)):
    """
    Export dataset with cleaning report and field mappings for manual Odoo import.

    This endpoint provides everything needed for a pre-Odoo data preparation workflow:
    - Cleaned and standardized data
    - Column-to-field mappings with target models
    - Cleaning report showing what was transformed
    - Selected modules for context

    Returns JSON with cleaned data and metadata ready for manual Odoo import.
    """
    dataset_service = DatasetService(db)
    mapping_service = MappingService(db)

    dataset = dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.cleaned_file_path or not Path(dataset.cleaned_file_path).exists():
        raise HTTPException(
            status_code=404,
            detail="No cleaned data available. Run profiling with cleaning enabled first."
        )

    # Get confirmed mappings
    mappings = mapping_service.get_mappings_for_dataset(dataset_id)
    confirmed_mappings = [m for m in mappings if m.chosen]

    if not confirmed_mappings:
        raise HTTPException(
            status_code=400,
            detail="No confirmed mappings found. Please confirm field mappings before exporting."
        )

    # Read cleaned data
    file_path = Path(dataset.cleaned_file_path)
    export_data = {
        "dataset_id": dataset_id,
        "dataset_name": dataset.name,
        "selected_modules": dataset.selected_modules or [],
        "cleaning_report": dataset.cleaning_report,
        "field_mappings": [],
        "sheets": {}
    }

    # Build field mappings structure
    for mapping in confirmed_mappings:
        export_data["field_mappings"].append({
            "source_column": mapping.header_name,
            "target_model": mapping.target_model,
            "target_field": mapping.target_field,
            "confidence": mapping.confidence,
            "rationale": mapping.rationale,
            "sheet_id": mapping.sheet_id
        })

    # Read cleaned data per sheet
    try:
        if file_path.suffix.lower() in ['.csv', '.cleaned.csv']:
            df = pd.read_csv(file_path)
            export_data["sheets"]["Sheet1"] = {
                "columns": df.columns.tolist(),
                "row_count": len(df),
                "data": df.to_dict('records')
            }
        else:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                export_data["sheets"][sheet_name] = {
                    "columns": df.columns.tolist(),
                    "row_count": len(df),
                    "data": df.to_dict('records')
                }

        # Add import instructions
        export_data["import_instructions"] = {
            "workflow": [
                "1. Review the field_mappings to understand how columns map to Odoo models/fields",
                "2. Use the cleaning_report to see what data transformations were applied",
                "3. Import sheets data to Odoo manually or via API using the field mappings",
                "4. Respect the topological order if importing related records (parents before children)"
            ],
            "models_detected": list(set(m.target_model for m in confirmed_mappings if m.target_model)),
            "cleaning_applied": dataset.cleaning_report is not None
        }

        return export_data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting data: {str(e)}"
        )
