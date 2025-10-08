from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Transform, Mapping
from app.services.transform_service import TransformService
from pydantic import BaseModel
from typing import Optional, List, Any

router = APIRouter()


class TransformCreate(BaseModel):
    fn: str
    params: Optional[dict] = None


class TransformResponse(BaseModel):
    id: int
    mapping_id: int
    order: int
    fn: str
    params: Optional[dict] = None

    class Config:
        from_attributes = True


class TransformUpdate(BaseModel):
    order: Optional[int] = None
    fn: Optional[str] = None
    params: Optional[dict] = None


class TestTransformRequest(BaseModel):
    fn: str
    params: Optional[dict] = None
    sample_value: Any


@router.get("/transforms/available")
async def get_available_transforms():
    """Get list of available transform functions with metadata."""
    return TransformService.get_available_transforms()


@router.get("/mappings/{mapping_id}/transforms", response_model=List[TransformResponse])
async def get_mapping_transforms(
    mapping_id: int,
    db: Session = Depends(get_db)
):
    """Get all transforms for a mapping, ordered by execution order."""
    transforms = db.query(Transform).filter(
        Transform.mapping_id == mapping_id
    ).order_by(Transform.order).all()

    return transforms


@router.post("/mappings/{mapping_id}/transforms", response_model=TransformResponse)
async def create_transform(
    mapping_id: int,
    transform: TransformCreate,
    db: Session = Depends(get_db)
):
    """Add a transform to a mapping."""
    # Verify mapping exists
    mapping = db.query(Mapping).filter(Mapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    # Get next order number
    max_order = db.query(Transform).filter(
        Transform.mapping_id == mapping_id
    ).count()

    new_transform = Transform(
        mapping_id=mapping_id,
        order=max_order,
        fn=transform.fn,
        params=transform.params
    )

    db.add(new_transform)
    db.commit()
    db.refresh(new_transform)

    return new_transform


@router.put("/transforms/{transform_id}", response_model=TransformResponse)
async def update_transform(
    transform_id: int,
    update: TransformUpdate,
    db: Session = Depends(get_db)
):
    """Update a transform."""
    transform = db.query(Transform).filter(Transform.id == transform_id).first()
    if not transform:
        raise HTTPException(status_code=404, detail="Transform not found")

    if update.order is not None:
        transform.order = update.order
    if update.fn is not None:
        transform.fn = update.fn
    if update.params is not None:
        transform.params = update.params

    db.commit()
    db.refresh(transform)

    return transform


@router.delete("/transforms/{transform_id}")
async def delete_transform(
    transform_id: int,
    db: Session = Depends(get_db)
):
    """Delete a transform."""
    transform = db.query(Transform).filter(Transform.id == transform_id).first()
    if not transform:
        raise HTTPException(status_code=404, detail="Transform not found")

    mapping_id = transform.mapping_id
    db.delete(transform)

    # Reorder remaining transforms
    remaining = db.query(Transform).filter(
        Transform.mapping_id == mapping_id
    ).order_by(Transform.order).all()

    for i, t in enumerate(remaining):
        t.order = i

    db.commit()

    return {"message": "Transform deleted"}


@router.post("/transforms/{transform_id}/reorder")
async def reorder_transform(
    transform_id: int,
    new_order: int,
    db: Session = Depends(get_db)
):
    """Reorder a transform in the execution chain."""
    transform = db.query(Transform).filter(Transform.id == transform_id).first()
    if not transform:
        raise HTTPException(status_code=404, detail="Transform not found")

    old_order = transform.order
    mapping_id = transform.mapping_id

    # Get all transforms for this mapping
    transforms = db.query(Transform).filter(
        Transform.mapping_id == mapping_id
    ).order_by(Transform.order).all()

    # Remove from old position
    transforms.pop(old_order)

    # Insert at new position
    transforms.insert(new_order, transform)

    # Update all orders
    for i, t in enumerate(transforms):
        t.order = i

    db.commit()

    return {"message": "Transform reordered"}


@router.post("/transforms/test")
async def test_transform(request: TestTransformRequest):
    """Test a transform function with a sample value."""
    try:
        result = TransformService.apply_transform(
            request.sample_value,
            request.fn,
            request.params
        )
        return {
            "input": request.sample_value,
            "output": result,
            "fn": request.fn,
            "params": request.params
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transform failed: {str(e)}")
