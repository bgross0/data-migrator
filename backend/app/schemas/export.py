"""
Pydantic schemas for export API.
"""
from pydantic import BaseModel
from typing import List, Dict


class ModelExportSummary(BaseModel):
    """Summary for a single model export."""

    model: str
    csv_filename: str
    rows_emitted: int
    exceptions_count: int


class ExportResponse(BaseModel):
    """Response from export endpoint."""

    dataset_id: int
    zip_path: str
    models: List[ModelExportSummary]
    total_emitted: int
    total_exceptions: int
    exceptions_by_code: Dict[str, int]
    message: str

    class Config:
        from_attributes = True
