"""
Pydantic schemas for exceptions API.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class ExceptionResponse(BaseModel):
    """Exception response schema."""

    id: int
    dataset_id: int
    model: str
    row_ptr: str
    error_code: str
    hint: str
    offending: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True


class ExceptionsListResponse(BaseModel):
    """List of exceptions with summary."""

    dataset_id: int
    model: Optional[str]
    total: int
    exceptions: list[ExceptionResponse]


class ExceptionsClearResponse(BaseModel):
    """Response after clearing exceptions."""

    dataset_id: int
    model: Optional[str]
    deleted_count: int
