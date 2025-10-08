from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.dataset_service import DatasetService
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetListResponse

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
