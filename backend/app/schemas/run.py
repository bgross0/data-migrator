from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.run import RunStatus


class RunCreate(BaseModel):
    graph_id: Optional[int] = None
    dry_run: bool = True


class RunBase(BaseModel):
    status: RunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    stats: Optional[Dict[str, Any]] = None


class RunResponse(RunBase):
    id: int
    dataset_id: int
    graph_id: Optional[int] = None

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    runs: List[RunResponse]
    total: int
