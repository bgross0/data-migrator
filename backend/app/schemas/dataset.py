from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class SheetBase(BaseModel):
    name: str
    n_rows: int
    n_cols: int


class SheetResponse(SheetBase):
    id: int
    dataset_id: int

    class Config:
        from_attributes = True


class DatasetCreate(BaseModel):
    name: str
    company_id: Optional[int] = None  # Multi-company support


class DatasetBase(BaseModel):
    name: str


class DatasetResponse(DatasetBase):
    id: int
    source_file_id: int
    created_at: datetime
    company_id: Optional[int] = None  # Multi-company support
    sheets: List[SheetResponse] = []

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]
    total: int
