"""
API routes for GraphSpec management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.graph_service import GraphService
from app.schemas.graph import (
    GraphSpec,
    GraphSpecCreate,
    GraphSpecUpdate,
    GraphValidation,
    GraphRunResponse
)
from typing import Dict, Any

router = APIRouter()


@router.post("/graphs", response_model=GraphSpec, status_code=status.HTTP_201_CREATED)
async def create_graph(graph_create: GraphSpecCreate, db: Session = Depends(get_db)):
    """Create a new graph definition"""
    service = GraphService(db)
    graph = service.create_graph(graph_create)

    return GraphSpec(**graph.spec)


@router.get("/graphs/{graph_id}", response_model=GraphSpec)
async def get_graph(graph_id: str, db: Session = Depends(get_db)):
    """Get a graph by ID"""
    service = GraphService(db)
    graph = service.get_graph(graph_id)

    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found"
        )

    return GraphSpec(**graph.spec)


@router.get("/graphs", response_model=List[GraphSpec])
async def list_graphs(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """List all graphs"""
    service = GraphService(db)
    graphs = service.list_graphs(limit=limit, offset=offset)

    return [GraphSpec(**g.spec) for g in graphs]


@router.put("/graphs/{graph_id}", response_model=GraphSpec)
async def update_graph(
    graph_id: str,
    graph_update: GraphSpecUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing graph"""
    service = GraphService(db)
    graph = service.update_graph(graph_id, graph_update)

    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found"
        )

    return GraphSpec(**graph.spec)


@router.delete("/graphs/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph(graph_id: str, db: Session = Depends(get_db)):
    """Delete a graph"""
    service = GraphService(db)
    success = service.delete_graph(graph_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found"
        )


@router.post("/graphs/{graph_id}/validate", response_model=GraphValidation)
async def validate_graph(graph_id: str, db: Session = Depends(get_db)):
    """Validate a graph for correctness"""
    service = GraphService(db)
    graph = service.get_graph(graph_id)

    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found"
        )

    graph_spec = GraphSpec(**graph.spec)
    validation = service.validate_graph(graph_spec)

    return validation


@router.post("/graphs/{graph_id}/run", response_model=GraphRunResponse)
async def run_graph(
    graph_id: str,
    dataset_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Execute a graph in the background using InlineTaskRunner.

    Returns immediately with a run ID that can be used to track progress.
    """
    service = GraphService(db)
    graph = service.get_graph(graph_id)

    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph {graph_id} not found"
        )

    # Validate first
    graph_spec = GraphSpec(**graph.spec)
    validation = service.validate_graph(graph_spec)

    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Graph validation failed: {validation.errors}"
        )

    # Create run record
    run = service.create_run(graph_id, dataset_id)

    # Execute the graph in background using shared task runner singleton
    from app.core.task_runner import get_task_runner
    from app.services.graph_execute_service import GraphExecuteService

    # Get shared task runner singleton
    task_runner = get_task_runner()

    def execute_graph_background():
        """Execute graph in background thread."""
        # Create new DB session for background thread
        from app.core.database import SessionLocal
        db_thread = SessionLocal()
        try:
            execute_service = GraphExecuteService(db_thread)
            result = execute_service.execute_graph_export(
                dataset_id=dataset_id,
                graph_id=graph_id,
                run_id=run.id  # Pass the run ID for concurrent safety
            )
            return result
        finally:
            db_thread.close()

    # Submit task for background execution
    task_id = task_runner.submit(
        execute_graph_background,
        task_id=run.id  # Use run ID as task ID
    )

    # Return immediately with run ID
    return GraphRunResponse(
        id=run.id,
        status="queued",
        message=f"Graph execution queued with task ID: {task_id}"
    )


@router.get("/graphs/{graph_id}/runs")
async def list_graph_runs(graph_id: str, db: Session = Depends(get_db)):
    """
    List all runs for a graph with detailed execution information.

    Returns array of runs including:
    - current_node: The model being processed in each run
    - context: Execution context with plan and progress details
    - logs: Array of timestamped log entries for each run
    """
    service = GraphService(db)
    runs = service.list_runs(graph_id=graph_id)

    return [
        {
            "id": run.id,
            "graph_id": run.graph_id,
            "dataset_id": run.dataset_id,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "progress": run.progress,
            "current_node": run.current_node,  # Direct access, no getattr
            "context": run.context or {},  # Direct access with default
            "logs": run.logs or [],  # Direct access with default
            "stats": run.stats,
            "error_message": run.error_message,
        }
        for run in runs
    ]


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str, db: Session = Depends(get_db)):
    """
    Get detailed status of a specific run.

    Returns complete execution state including:
    - current_node: The model being processed
    - context: Execution context with plan and progress details
    - logs: Array of timestamped log entries
    """
    service = GraphService(db)
    run = service.get_run(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found"
        )

    # Ensure all fields are properly exposed
    return {
        "id": run.id,
        "graph_id": run.graph_id,
        "dataset_id": run.dataset_id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "progress": run.progress,
        "current_node": run.current_node,  # Direct access, no getattr
        "context": run.context or {},  # Direct access with default
        "logs": run.logs or [],  # Direct access with default
        "stats": run.stats,
        "error_message": run.error_message,
    }


# Registry Integration Endpoints

@router.post("/graphs/registry/{template_type}")
async def create_registry_graph(template_type: str, db: Session = Depends(get_db)):
    """Generate graph from registry template"""
    service = GraphService(db)
    
    try:
        graph = service.create_from_registry(template_type)
        return GraphSpec(**graph.spec)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/graphs/registry/templates")
async def list_registry_templates(db: Session = Depends(get_db)):
    """List available registry-based templates"""
    service = GraphService(db)
    templates = service.list_registry_templates()
    
    return {
        "templates": templates,
        "total": len(templates)
    }


@router.post("/graphs/{graph_id}/validate/registry")
async def validate_graph_registry(graph_id: str, db: Session = Depends(get_db)):
    """Validate graph against current registry"""
    service = GraphService(db)
    
    try:
        validation = service.validate_registry_compatibility(graph_id)
        return validation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/graphs/registry/dependencies/{model_name}")
async def get_registry_dependencies(model_name: str, db: Session = Depends(get_db)):
    """Get dependency information for a specific model from registry"""
    service = GraphService(db)
    dependencies = service.get_registry_dependencies(model_name)
    
    if not dependencies["available"] and "error" in dependencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=dependencies["error"]
        )

    return dependencies
