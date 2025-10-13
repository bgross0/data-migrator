"""
Operations API - Endpoints for tracking operation progress.
"""
from fastapi import APIRouter, HTTPException
from app.services.operation_tracker import OperationTracker

router = APIRouter()


@router.get("/operations/{operation_id}/status")
async def get_operation_status(operation_id: str):
    """
    Get the current status of an operation.

    Frontend polls this endpoint to get real-time progress updates.

    Returns:
        {
            "id": "uuid",
            "operation_type": "upload",
            "status": "running" | "complete" | "error",
            "progress": 45.5,
            "current_step": "Profiling columns",
            "steps": [
                {"id": "step1", "label": "Upload", "status": "complete", "detail": "..."},
                {"id": "step2", "label": "Profile", "status": "in_progress", "detail": "..."},
                ...
            ],
            "result": {...},  // Present when complete
            "error": "...",   // Present when error
        }
    """
    tracker = OperationTracker.get(operation_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Operation not found")

    try:
        status = tracker.get_status()
        return status
    finally:
        tracker.close()
