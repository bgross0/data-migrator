from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.field_detector import FieldTypeDetector
from app.services.addon_generator import OdooAddonGenerator
from app.models import ColumnProfile
from app.schemas.mapping import FieldTypeSuggestion

router = APIRouter()


@router.get("/mappings/{mapping_id}/suggest-field-type", response_model=FieldTypeSuggestion)
async def suggest_field_type(
    mapping_id: int,
    column_profile_id: int,
    db: Session = Depends(get_db)
):
    """Suggest Odoo field type for a column based on its profile."""
    profile = db.query(ColumnProfile).filter(ColumnProfile.id == column_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Column profile not found")

    suggestion = FieldTypeDetector.detect_field_type(
        dtype_guess=profile.dtype_guess,
        patterns=profile.patterns or {},
        null_pct=profile.null_pct,
        distinct_pct=profile.distinct_pct,
        sample_values=profile.sample_values or []
    )

    return suggestion


@router.post("/datasets/{dataset_id}/addon/generate")
async def generate_addon(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Generate Odoo addon module from custom field mappings."""
    try:
        generator = OdooAddonGenerator(db)
        zip_buffer = generator.generate_addon(dataset_id)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=custom_fields_migration.zip"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/datasets/{dataset_id}/addon/instructions")
async def get_installation_instructions(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Get installation instructions for the addon."""
    generator = OdooAddonGenerator(db)
    instructions = generator.get_installation_instructions("custom_fields_migration")

    return {"instructions": instructions}
