"""
Pydantic schemas for GraphSpec
Mirror of frontend/src/types/graph.ts
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime


NodeKind = Literal['sheet', 'model', 'field', 'transform', 'join', 'loader', 'validator']
EdgeKind = Literal['map', 'flow', 'depends', 'filter']


class GraphNodeData(BaseModel):
    """Node data - flexible dict with optional fields"""
    # sheet
    sheetName: Optional[str] = None
    samplePath: Optional[str] = None
    # model/field
    odooModel: Optional[str] = None
    fieldName: Optional[str] = None
    dtype: Optional[str] = None
    # transform
    transformId: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    # join/lookup
    leftKey: Optional[str] = None
    rightModel: Optional[str] = None
    rightField: Optional[str] = None
    # loader
    upsertKey: Optional[List[str]] = None


class GraphNode(BaseModel):
    id: str
    kind: NodeKind
    label: str
    data: GraphNodeData
    position: Optional[Dict[str, float]] = None  # {x: float, y: float}


class GraphEdgeData(BaseModel):
    """Edge data - optional metadata"""
    sourceColumn: Optional[str] = None
    transformChain: Optional[List[str]] = None


class GraphEdge(BaseModel):
    id: str
    from_: str  # 'from' is reserved in Python, use from_ and alias
    to: str
    kind: EdgeKind
    data: Optional[GraphEdgeData] = None

    class Config:
        populate_by_name = True
        # Allow 'from' in JSON to map to 'from_'
        json_schema_extra = {
            "properties": {
                "from": {"type": "string"}
            }
        }


class GraphSpec(BaseModel):
    id: str
    name: str
    version: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: Optional[Dict[str, Any]] = None


class GraphSpecCreate(BaseModel):
    """For creating a new graph spec"""
    name: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: Optional[Dict[str, Any]] = None


class GraphSpecUpdate(BaseModel):
    """For updating an existing graph spec"""
    name: Optional[str] = None
    nodes: Optional[List[GraphNode]] = None
    edges: Optional[List[GraphEdge]] = None
    metadata: Optional[Dict[str, Any]] = None


# Validation
class ValidationError(BaseModel):
    nodeId: Optional[str] = None
    edgeId: Optional[str] = None
    message: str
    type: Literal['missing_field', 'type_mismatch', 'circular_dependency', 'invalid_config']


class ValidationWarning(BaseModel):
    nodeId: Optional[str] = None
    edgeId: Optional[str] = None
    message: str
    type: Literal['low_confidence', 'missing_transform', 'performance']


class GraphValidation(BaseModel):
    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]


# Run status
class RunLog(BaseModel):
    timestamp: datetime
    level: Literal['debug', 'info', 'warning', 'error']
    nodeId: Optional[str] = None
    message: str


class GraphRunStats(BaseModel):
    nodesProcessed: int
    totalNodes: int
    rowsImported: int
    errors: int


class GraphRun(BaseModel):
    id: str
    graphId: str
    status: Literal['queued', 'running', 'completed', 'failed']
    startedAt: datetime
    finishedAt: Optional[datetime] = None
    progress: int  # 0-100
    logs: List[RunLog]
    stats: Optional[GraphRunStats] = None


class GraphRunResponse(BaseModel):
    """Response when creating a run"""
    id: str
    status: str
    message: str
