from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Sheet, ColumnProfile
from app.core.config import settings
from pathlib import Path

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


@router.get("/sheets/{sheet_id}/download")
async def download_sheet(sheet_id: int, db: Session = Depends(get_db)):
    """Download a split sheet as CSV file."""
    sheet = db.query(Sheet).filter(Sheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # Look for split sheet file
    storage_path = Path(settings.STORAGE_PATH) / "split_sheets"
    file_pattern = f"dataset_{sheet.dataset_id}_{sheet.name}.csv"
    file_path = storage_path / file_pattern

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Split sheet file not found. This sheet may not have been split yet."
        )

    return FileResponse(
        path=str(file_path),
        filename=f"{sheet.name}.csv",
        media_type="text/csv"
    )
