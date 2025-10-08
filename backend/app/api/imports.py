from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.import_service import ImportService
from app.schemas.run import RunResponse, RunListResponse, RunCreate

router = APIRouter()


@router.post("/datasets/{dataset_id}/runs", response_model=RunResponse)
async def create_run(
    dataset_id: int,
    run_data: RunCreate,
    db: Session = Depends(get_db),
):
    """Create a new import run (dry-run or execute)."""
    service = ImportService(db)
    run = await service.create_run(dataset_id, run_data)
    return run


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all import runs."""
    service = ImportService(db)
    runs = service.list_runs(skip=skip, limit=limit)
    return {"runs": runs, "total": len(runs)}


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get a specific run by ID."""
    service = ImportService(db)
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/runs/{run_id}/rollback")
async def rollback_run(run_id: int, db: Session = Depends(get_db)):
    """Rollback an import run."""
    service = ImportService(db)
    success = await service.rollback_run(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="Rollback failed")
    return {"status": "rolled_back"}
