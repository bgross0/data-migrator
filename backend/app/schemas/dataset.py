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


class DatasetBase(BaseModel):
    name: str


class DatasetResponse(DatasetBase):
    id: int
    source_file_id: int
    created_at: datetime
    sheets: List[SheetResponse] = []

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]
    total: int
