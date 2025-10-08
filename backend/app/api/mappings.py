from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.mapping_service import MappingService
from app.schemas.mapping import MappingResponse, MappingUpdate, MappingListResponse

router = APIRouter()


@router.get("/datasets/{dataset_id}/mappings", response_model=MappingListResponse)
async def get_dataset_mappings(dataset_id: int, db: Session = Depends(get_db)):
    """Get all mappings for a dataset."""
    service = MappingService(db)
    mappings = service.get_mappings_for_dataset(dataset_id)
    return {"mappings": mappings, "total": len(mappings)}


@router.post("/datasets/{dataset_id}/mappings/generate")
async def generate_mappings(dataset_id: int, db: Session = Depends(get_db)):
    """Generate mapping suggestions for a dataset."""
    service = MappingService(db)
    mappings = await service.generate_mappings(dataset_id)
    return {"mappings": mappings, "total": len(mappings)}


@router.put("/mappings/{mapping_id}", response_model=MappingResponse)
async def update_mapping(
    mapping_id: int,
    mapping_data: MappingUpdate,
    db: Session = Depends(get_db),
):
    """Update a mapping (confirm, ignore, or change target)."""
    service = MappingService(db)
    mapping = service.update_mapping(mapping_id, mapping_data)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """Delete a mapping."""
    service = MappingService(db)
    success = service.delete_mapping(mapping_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"status": "deleted"}
