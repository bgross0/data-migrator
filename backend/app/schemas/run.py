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
    current_node: Optional[str] = None
    progress: int = 0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    runs: List[RunResponse]
    total: int


class GraphExecutionPlan(BaseModel):
    """Plan for executing a graph-based export"""
    execution_order: List[str]  # Node IDs in execution order
    phases: List[Dict[str, Any]]  # Group information
    estimated_duration_minutes: int
    requirements: List[str]
