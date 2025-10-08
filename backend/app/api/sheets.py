from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Sheet, ColumnProfile

router = APIRouter()


@router.get("/sheets/{sheet_id}/profiles")
async def get_sheet_profiles(sheet_id: int, db: Session = Depends(get_db)):
    """Get all column profiles for a sheet."""
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")

    profiles = db.query(ColumnProfile).filter(ColumnProfile.sheet_id == sheet_id).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "dtype_guess": p.dtype_guess,
            "null_pct": p.null_pct,
            "distinct_pct": p.distinct_pct,
            "patterns": p.patterns or {},
            "sample_values": p.sample_values or [],
        }
        for p in profiles
    ]
