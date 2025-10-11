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

    # Explicitly convert SQLAlchemy objects to dicts for proper serialization
    mapping_responses = []
    for mapping in mappings:
        mapping_dict = {
            "id": mapping.id,
            "dataset_id": mapping.dataset_id,
            "sheet_id": mapping.sheet_id,
            "header_name": mapping.header_name,
            "target_model": mapping.target_model,
            "target_field": mapping.target_field,
            "confidence": mapping.confidence if mapping.confidence is not None else 0.0,
            "status": mapping.status,
            "chosen": mapping.chosen,
            "rationale": mapping.rationale,
            "custom_field_definition": mapping.custom_field_definition,
            "transforms": [
                {
                    "id": t.id,
                    "mapping_id": t.mapping_id,
                    "order": t.order,
                    "fn": t.fn,
                    "params": t.params
                } for t in mapping.transforms
            ] if mapping.transforms else [],
            "suggestions": [
                {
                    "id": s.id,
                    "mapping_id": s.mapping_id,
                    "candidates": s.candidates
                } for s in mapping.suggestions
            ] if mapping.suggestions else []
        }
        mapping_responses.append(mapping_dict)

    return {"mappings": mapping_responses, "total": len(mapping_responses)}


@router.post("/datasets/{dataset_id}/mappings/generate", response_model=MappingListResponse)
async def generate_mappings(
    dataset_id: int,
    use_deterministic: bool = True,
    db: Session = Depends(get_db)
):
    """
    Generate mapping suggestions for a dataset.

    Args:
        dataset_id: ID of the dataset
        use_deterministic: Use deterministic field mapper (odoo-dictionary based) if True,
                          use hardcoded mappings if False. Defaults to True.
    """
    service = MappingService(db)
    mappings = await service.generate_mappings_v2(dataset_id, use_deterministic=use_deterministic)

    # Explicitly convert SQLAlchemy objects to dicts for proper serialization
    mapping_responses = []
    for mapping in mappings:
        mapping_dict = {
            "id": mapping.id,
            "dataset_id": mapping.dataset_id,
            "sheet_id": mapping.sheet_id,
            "header_name": mapping.header_name,
            "target_model": mapping.target_model,
            "target_field": mapping.target_field,
            "confidence": mapping.confidence if mapping.confidence is not None else 0.0,
            "status": mapping.status,
            "chosen": mapping.chosen,
            "rationale": mapping.rationale,
            "custom_field_definition": mapping.custom_field_definition,
            "transforms": [
                {
                    "id": t.id,
                    "mapping_id": t.mapping_id,
                    "order": t.order,
                    "fn": t.fn,
                    "params": t.params
                } for t in mapping.transforms
            ] if hasattr(mapping, 'transforms') and mapping.transforms else [],
            "suggestions": [
                {
                    "id": s.id,
                    "mapping_id": s.mapping_id,
                    "candidates": s.candidates
                } for s in mapping.suggestions
            ] if hasattr(mapping, 'suggestions') and mapping.suggestions else []
        }
        mapping_responses.append(mapping_dict)

    return {"mappings": mapping_responses, "total": len(mapping_responses)}


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
