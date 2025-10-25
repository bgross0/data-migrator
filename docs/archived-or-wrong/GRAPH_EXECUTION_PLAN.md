# Graph Execution Implementation Plan

## Objective
Make `POST /graphs/{id}/run` actually execute multi-model imports using topological ordering.

---

## Current State Analysis

### What Exists
1. **`GraphExecuteService`** (`backend/app/services/graph_execute_service.py`)
   - ✓ Lines 1-100: Execution plan generation with topological sort
   - ✓ Lines 150-250: Full execution logic (but never called)
   - ✓ Handles dependencies, progress tracking, error handling

2. **GraphRun Model** (`backend/app/models/graph.py`)
   - ✓ Stores: graph_id, dataset_id, status, progress, metadata
   - ✓ Status enum: pending, running, completed, failed
   - ✓ progress field (JSON) for per-node tracking

3. **Graph API** (`backend/app/api/graphs.py`)
   - ✓ Lines 104-144: `run_graph()` endpoint
   - ✗ Line 136: TODO - doesn't actually execute

4. **Celery Config** (`backend/app/core/celery_app.py`)
   - ✓ Configured with Redis broker
   - ✓ Includes import_tasks module
   - ✓ Task limits: 1 hour max, 55 min soft

### What's Missing
1. Celery task to execute graph
2. Endpoint wiring to enqueue task
3. Progress update mechanism
4. Error handling in execution flow

---

## Implementation Steps

### Step 1: Add Graph Execution Celery Task
**File**: `backend/app/services/import_tasks.py`

**Add Task**:
```python
@celery_app.task(name="execute_graph", bind=True)
def execute_graph(self, graph_run_id: str):
    """
    Execute a graph-based multi-model import.

    Args:
        graph_run_id: ID of GraphRun to execute

    Returns:
        Dict with status, stats, errors
    """
    db = SessionLocal()
    try:
        # 1. Load GraphRun
        graph_run = db.query(GraphRun).filter(GraphRun.id == graph_run_id).first()
        if not graph_run:
            return {"error": "GraphRun not found", "graph_run_id": graph_run_id}

        # 2. Update status to running
        graph_run.status = "running"
        graph_run.started_at = datetime.utcnow()
        db.commit()

        # 3. Load Graph spec
        graph = db.query(Graph).filter(Graph.id == graph_run.graph_id).first()
        if not graph:
            graph_run.status = "failed"
            graph_run.error_message = "Graph not found"
            db.commit()
            return {"error": "Graph not found"}

        graph_spec = GraphSpec(**graph.spec)

        # 4. Initialize GraphExecuteService
        execute_service = GraphExecuteService(db)

        # 5. Execute the graph (this does the actual work)
        result = execute_service.execute_graph(
            graph_spec=graph_spec,
            graph_run_id=graph_run_id,
            dataset_id=graph_run.dataset_id,
            dry_run=False,
            progress_callback=lambda progress: update_progress(graph_run_id, progress)
        )

        # 6. Update final status
        graph_run.status = result["status"]  # "completed" or "failed"
        graph_run.completed_at = datetime.utcnow()
        graph_run.stats = result.get("stats", {})
        graph_run.error_message = result.get("error")
        db.commit()

        return result

    except Exception as e:
        # Catch any unexpected errors
        if 'graph_run' in locals():
            graph_run.status = "failed"
            graph_run.error_message = str(e)
            graph_run.completed_at = datetime.utcnow()
            db.commit()
        return {"error": str(e), "graph_run_id": graph_run_id}
    finally:
        db.close()


def update_progress(graph_run_id: str, progress: dict):
    """Update GraphRun progress in real-time."""
    db = SessionLocal()
    try:
        graph_run = db.query(GraphRun).filter(GraphRun.id == graph_run_id).first()
        if graph_run:
            graph_run.progress = progress
            db.commit()
    finally:
        db.close()
```

**Changes Required**:
- Add imports: `from datetime import datetime`
- Add helper function: `update_progress()`

---

### Step 2: Modify GraphExecuteService.execute_graph()
**File**: `backend/app/services/graph_execute_service.py`

**Current Issue**: Method exists but signature may not match task expectations

**Check**:
1. Does `execute_graph()` method exist? (Line ~150)
2. Does it accept `progress_callback`?
3. Does it return proper status dict?

**Expected Method Signature**:
```python
def execute_graph(
    self,
    graph_spec: GraphSpec,
    graph_run_id: str,
    dataset_id: int,
    dry_run: bool = False,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Execute graph in topological order.

    Returns:
        {
            "status": "completed" | "failed",
            "stats": {
                "nodes_executed": int,
                "nodes_failed": int,
                "total_records": int
            },
            "error": Optional[str]
        }
    """
```

**Implementation Logic**:
1. Get execution order from topological sort
2. For each node in order:
   a. Extract model name from node.data.odooModel
   b. Get dataset sheet data
   c. Load mapping for this model
   d. Execute import for this model
   e. Update progress via callback
   f. Handle errors gracefully (continue or halt based on criticality)
3. Return aggregate results

---

### Step 3: Wire Up API Endpoint
**File**: `backend/app/api/graphs.py`

**Current Code** (Lines 104-144):
```python
@router.post("/graphs/{graph_id}/run", response_model=GraphRunResponse)
async def run_graph(
    graph_id: str,
    dataset_id: int = None,
    db: Session = Depends(get_db)
):
    # ... validation ...

    # Create run record
    run = service.create_run(graph_id, dataset_id)

    # TODO: Enqueue Celery task here  <-- LINE 136
    # from app.tasks.graph_tasks import execute_graph
    # task = execute_graph.delay(run.id)
```

**Replace With**:
```python
@router.post("/graphs/{graph_id}/run", response_model=GraphRunResponse)
async def run_graph(
    graph_id: str,
    dataset_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Execute a graph (enqueues Celery task for async execution)
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

    # Create GraphRun record
    run = service.create_run(graph_id, dataset_id)

    # Enqueue Celery task for async execution
    from app.services.import_tasks import execute_graph
    task = execute_graph.delay(run.id)

    return GraphRunResponse(
        id=run.id,
        status=run.status,
        task_id=task.id,  # Return Celery task ID for polling
        message="Graph execution started"
    )
```

**Changes Required**:
- Add `task_id` field to `GraphRunResponse` schema
- Import the task function
- Call `task.delay(run.id)`

---

### Step 4: Update GraphRunResponse Schema
**File**: `backend/app/schemas/graph.py`

**Add Field**:
```python
class GraphRunResponse(BaseModel):
    id: str
    status: str
    message: str
    task_id: Optional[str] = None  # <-- ADD THIS
```

---

### Step 5: Implement GraphExecuteService.execute_graph()
**File**: `backend/app/services/graph_execute_service.py`

**Check if Method Exists** (around line 150):
- If exists but incomplete, finish it
- If doesn't exist, create it

**Full Implementation**:
```python
def execute_graph(
    self,
    graph_spec: GraphSpec,
    graph_run_id: str,
    dataset_id: int,
    dry_run: bool = False,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """Execute graph in topological order."""

    # 1. Create execution plan
    plan = self.create_execution_plan(graph_spec)
    execution_order = plan.execution_order

    # Initialize stats
    stats = {
        "nodes_executed": 0,
        "nodes_failed": 0,
        "total_records": 0,
        "node_results": {}
    }

    # Initialize Odoo connector
    odoo = OdooConnector(
        url=settings.ODOO_URL,
        db=settings.ODOO_DB,
        username=settings.ODOO_USERNAME,
        password=settings.ODOO_PASSWORD
    )
    odoo.authenticate()

    # 2. Execute each model in topological order
    for idx, model_name in enumerate(execution_order):
        try:
            # Update progress
            if progress_callback:
                progress_callback({
                    "current_node": model_name,
                    "current_index": idx,
                    "total_nodes": len(execution_order),
                    "percentage": int((idx / len(execution_order)) * 100)
                })

            # Execute import for this model
            result = self._execute_node(
                model_name=model_name,
                dataset_id=dataset_id,
                graph_run_id=graph_run_id,
                odoo=odoo,
                dry_run=dry_run
            )

            stats["nodes_executed"] += 1
            stats["total_records"] += result.get("records_imported", 0)
            stats["node_results"][model_name] = result

        except Exception as e:
            stats["nodes_failed"] += 1
            stats["node_results"][model_name] = {
                "status": "failed",
                "error": str(e)
            }

            # Decide: continue or halt?
            # For now, continue to next model
            logger.error(f"Failed to execute node {model_name}: {e}")

    # 3. Determine final status
    if stats["nodes_failed"] > 0:
        status_str = "completed_with_errors"
    else:
        status_str = "completed"

    # Final progress update
    if progress_callback:
        progress_callback({
            "current_node": None,
            "current_index": len(execution_order),
            "total_nodes": len(execution_order),
            "percentage": 100
        })

    return {
        "status": status_str,
        "stats": stats,
        "error": None if stats["nodes_failed"] == 0 else f"{stats['nodes_failed']} nodes failed"
    }


def _execute_node(
    self,
    model_name: str,
    dataset_id: int,
    graph_run_id: str,
    odoo: OdooConnector,
    dry_run: bool
) -> Dict[str, Any]:
    """Execute import for a single node/model."""

    # Get mapping for this model (assumes mapping exists)
    # In reality, you'd query Mapping table by dataset_id and target_model

    # For now, delegate to ImportService
    result = self.import_service.execute_import(
        dataset_id=dataset_id,
        odoo=odoo,
        dry_run=dry_run,
        target_model=model_name,  # Filter to this specific model
        graph_run_id=graph_run_id
    )

    return {
        "status": "completed",
        "records_imported": result.stats.get("created", 0)
    }
```

**Key Points**:
- Uses topological sort from `create_execution_plan()`
- Calls `_execute_node()` for each model
- Updates progress via callback
- Aggregates stats
- Handles errors gracefully

---

### Step 6: Update GraphService.create_run()
**File**: `backend/app/services/graph_service.py`

**Verify Method**:
```python
def create_run(self, graph_id: str, dataset_id: Optional[int] = None) -> GraphRun:
    """Create a new GraphRun record."""
    graph_run = GraphRun(
        id=str(uuid.uuid4()),
        graph_id=graph_id,
        dataset_id=dataset_id,
        status="pending",
        progress={},
        metadata={}
    )
    self.db.add(graph_run)
    self.db.commit()
    self.db.refresh(graph_run)
    return graph_run
```

**Ensure Returns GraphRun Object** (not dict)

---

### Step 7: Add Progress Polling Endpoint
**File**: `backend/app/api/graphs.py`

**Add New Endpoint**:
```python
@router.get("/graph-runs/{run_id}/progress")
async def get_graph_run_progress(run_id: str, db: Session = Depends(get_db)):
    """Get real-time progress of a graph execution."""
    graph_run = db.query(GraphRun).filter(GraphRun.id == run_id).first()

    if not graph_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GraphRun {run_id} not found"
        )

    return {
        "id": graph_run.id,
        "status": graph_run.status,
        "progress": graph_run.progress,
        "stats": graph_run.stats,
        "error_message": graph_run.error_message,
        "started_at": graph_run.started_at,
        "completed_at": graph_run.completed_at
    }
```

**Purpose**: Frontend can poll this to show progress bar

---

## Testing Plan

### Unit Tests
1. Test `execute_graph()` task with mock GraphRun
2. Test `GraphExecuteService.execute_graph()` with sample graph
3. Test topological sort produces correct order

### Integration Tests
1. Create simple 2-node graph (res.partner → crm.lead)
2. POST to `/graphs/{id}/run`
3. Verify:
   - Task enqueued (task_id returned)
   - GraphRun status = "running"
   - Progress updates
   - Final status = "completed"
   - Records created in Odoo

### Manual Testing
1. Start Celery worker: `celery -A app.core.celery_app worker --loglevel=info`
2. Start backend: `uvicorn app.main:app --reload`
3. Upload dataset
4. Create graph via QuickStart template
5. Execute: `POST /graphs/{id}/run`
6. Poll progress: `GET /graph-runs/{run_id}/progress`
7. Verify completion

---

## Files to Modify

| File | Action | Lines |
|------|--------|-------|
| `backend/app/services/import_tasks.py` | Add execute_graph task | +60 |
| `backend/app/api/graphs.py` | Wire up endpoint | ~10 (replace TODO) |
| `backend/app/services/graph_execute_service.py` | Implement execute_graph() | +80 |
| `backend/app/schemas/graph.py` | Add task_id field | +1 |
| `backend/app/api/graphs.py` | Add progress endpoint | +20 |

**Total**: ~171 lines of code

---

## Success Criteria

- [ ] `POST /graphs/{id}/run` returns task_id and status="running"
- [ ] Celery task executes and updates GraphRun.status
- [ ] Progress updates in real-time (can poll `/graph-runs/{id}/progress`)
- [ ] Multi-model imports complete in topological order
- [ ] Parents imported before children
- [ ] Final status = "completed" on success
- [ ] Errors logged and GraphRun.status = "failed" on failure
- [ ] No more TODO markers in graph execution code

---

## Rollback Plan

If implementation breaks:
1. Revert `graphs.py` to TODO state
2. Keep task code but don't call it
3. Graph CRUD still works, just not execution

---

## Timeline

- **Step 1-4**: 30 minutes (add task, wire endpoint, update schema)
- **Step 5**: 45 minutes (implement execute_graph logic)
- **Step 6-7**: 15 minutes (verify create_run, add progress endpoint)
- **Testing**: 30 minutes (manual + integration tests)

**Total**: ~2 hours

---

## Next Steps After Completion

Once graph execution works:
1. Fix template progress tracking (query GraphRun completion)
2. Implement rollback (query KeyMap and delete)
3. Wire up FlowView frontend
4. Complete Runs page

This is the ONLY blocker. Everything else depends on graph execution working.
