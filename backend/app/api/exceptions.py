"""
Exceptions API endpoints.

Provides GET/DELETE operations for validation exceptions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.adapters.repositories_sqlite import SQLiteExceptionsRepo
from app.schemas.exception import (
    ExceptionsListResponse,
    ExceptionsClearResponse,
    ExceptionResponse,
)

router = APIRouter()


@router.get("/datasets/{dataset_id}/exceptions", response_model=ExceptionsListResponse)
def list_exceptions(
    dataset_id: int,
    model: Optional[str] = Query(None, description="Filter by model (e.g., res.partner)"),
    db: Session = Depends(get_db),
):
    """
    List validation exceptions for a dataset.

    Args:
        dataset_id: ID of the dataset
        model: Optional model filter

    Returns:
        List of exceptions with error codes, hints, and offending data
    """
    repo = SQLiteExceptionsRepo(db)

    exceptions = repo.list(dataset_id, model)
    total = len(exceptions)

    return ExceptionsListResponse(
        dataset_id=dataset_id,
        model=model,
        total=total,
        exceptions=[ExceptionResponse(**exc) for exc in exceptions],
    )


@router.delete(
    "/datasets/{dataset_id}/exceptions", response_model=ExceptionsClearResponse
)
def clear_exceptions(
    dataset_id: int,
    model: Optional[str] = Query(None, description="Filter by model (e.g., res.partner)"),
    db: Session = Depends(get_db),
):
    """
    Clear validation exceptions for a dataset.

    Args:
        dataset_id: ID of the dataset
        model: Optional model filter (if None, clears all exceptions)

    Returns:
        Count of deleted exceptions
    """
    repo = SQLiteExceptionsRepo(db)

    deleted_count = repo.clear(dataset_id, model)
    db.commit()

    return ExceptionsClearResponse(
        dataset_id=dataset_id,
        model=model,
        deleted_count=deleted_count,
    )


@router.get("/datasets/{dataset_id}/exceptions/count")
def count_exceptions(
    dataset_id: int,
    model: Optional[str] = Query(None, description="Filter by model"),
    db: Session = Depends(get_db),
):
    """
    Count exceptions for a dataset.

    Args:
        dataset_id: ID of the dataset
        model: Optional model filter

    Returns:
        Count of exceptions
    """
    repo = SQLiteExceptionsRepo(db)
    count = repo.count(dataset_id, model)

    return {"dataset_id": dataset_id, "model": model, "count": count}
