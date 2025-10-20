# INCOMPLETE FEATURES - WHAT YOU ASKED FOR THAT ISN'T DONE

**Last Updated**: 2025-10-19

## Summary

You asked for complete implementations of:
1. Template system with progress tracking
2. Graph execution engine
3. AI assistant with MCP integration
4. Rollback functionality
5. Async task execution

**Reality**: Infrastructure exists but critical execution logic has TODO markers and doesn't work.

---

## 1. GRAPH EXECUTION - NOT WORKING

### What You Asked For
Execute multi-model imports using graph-based topological ordering

### What's Implemented
- ✓ Graph CRUD (create, read, update, delete)
- ✓ GraphSpec validation
- ✓ Topological sorting algorithm
- ✓ Execution plan generation
- ✓ GraphExecuteService with full logic

### What's BROKEN
❌ **Line `backend/app/api/graphs.py:112`**
```python
"""
Execute a graph (enqueue Celery task)
TODO: Implement actual Celery task execution
"""
```

❌ **Line `backend/app/api/graphs.py:136`**
```python
# TODO: Enqueue Celery task here
# from app.tasks.graph_tasks import execute_graph
# task = execute_graph.delay(run.id)
```

### Impact
- `POST /graphs/{id}/run` creates a run record but **DOES NOT EXECUTE**
- GraphExecuteService has full implementation but **NOBODY CALLS IT**
- Progress tracking schema exists but **NEVER GETS UPDATED**

### What Needs to Be Done
1. Create `backend/app/tasks/graph_tasks.py` with `execute_graph` task
2. Call `GraphExecuteService.execute()` from the task
3. Update progress in real-time
4. Wire up the endpoint to actually enqueue the task

---

## 2. TEMPLATE PROGRESS TRACKING - FAKE DATA

### What You Asked For
Show users which models in a template have been completed

### What's Implemented
- ✓ Template JSON definitions
- ✓ Template loading and instantiation
- ✓ Progress API endpoint exists

### What's BROKEN
❌ **Line `backend/app/services/template_service.py:59`**
```python
completed=False  # TODO: Check against completed runs
```

❌ **Line `backend/app/services/template_service.py:111`**
```python
# TODO: Query GraphRun table to find completed models
```

### Impact
- Progress API returns **FAKE DATA** - always shows 0% completion
- Doesn't query database to check actual GraphRun status
- Users have no visibility into what's actually been done

### What Needs to Be Done
1. Query GraphRun table for template's graph_id
2. Check which nodes have `status='completed'`
3. Return actual completion percentage
4. Update each step's `completed` flag based on DB state

---

## 3. AI ASSISTANT MCP INTEGRATION - NOT CONNECTED

### What You Asked For
Web chat that uses MCP tools to give Claude Code visibility into the system

### What's Implemented
- ✓ MCP server with 20+ tools (works in VSCode)
- ✓ Web chat UI component
- ✓ Assistant API endpoint with intent routing

### What's BROKEN
❌ **Line `backend/app/api/assistant.py:182`**
```python
async def call_mcp_tool(tool_name: str, params: Optional[Dict] = None) -> Dict:
    """
    Call an MCP tool via subprocess or HTTP.

    This is a simplified version - in production, you'd want to:
    1. Use a proper MCP client library
    2. Cache connections
    3. Handle streaming responses
    """

    # For now, directly call the API endpoints that MCP would call
    # This bypasses MCP but gives the same functionality
```

### Impact
- Web chat **DOES NOT USE MCP** - just calls HTTP endpoints directly
- It's keyword matching, not AI-powered
- MCP server exists but only works in VSCode, not web UI
- The "AI assistant" is a glorified string matcher

### What Needs to Be Done
1. Install MCP client library in backend
2. Connect to MCP server via stdio or HTTP
3. Call actual MCP tools from `call_mcp_tool()`
4. Handle streaming responses
5. OR: Make it clear this is just keyword matching, not AI

---

## 4. ROLLBACK - NOT IMPLEMENTED

### What You Asked For
Ability to undo/rollback failed or incorrect imports

### What's Implemented
- ✓ KeyMap tracks source→odoo_id mappings
- ✓ RunLog tracks all operations
- ✓ Rollback API endpoint exists

### What's BROKEN
❌ **Line `backend/app/services/import_service.py:272`**
```python
# TODO: Implement rollback logic
```

### Impact
- `POST /runs/{id}/rollback` endpoint exists but **DOES NOTHING**
- Users can't undo imports
- Must manually delete records in Odoo

### What Needs to Be Done
1. Query KeyMap for all odoo_ids created in this run
2. Call Odoo's `unlink()` method for each record
3. Delete in reverse topological order (children → parents)
4. Mark run as `status='rolled_back'`
5. Clear KeyMap entries for this run

---

## 5. ASYNC TASK EXECUTION - RUNS SYNCHRONOUSLY

### What You Asked For
Background task execution so imports don't block the API

### What's Implemented
- ✓ Celery config exists (`backend/app/core/celery_app.py`)
- ✓ Some profiler tasks use Celery
- ✓ InlineTaskRunner for sync fallback

### What's BROKEN
❌ **Line `backend/app/services/import_service.py:34`**
```python
# TODO: Trigger import task asynchronously
```

### Impact
- Imports run **SYNCHRONOUSLY** - API request waits for entire import
- Large imports will timeout
- No progress updates during import
- Can't run multiple imports in parallel

### What Needs to Be Done
1. Create `backend/app/tasks/import_tasks.py`
2. Move import logic to Celery task
3. Return task_id immediately from API
4. Poll task status for progress
5. OR: Use the InlineTaskRunner in thread mode for now

---

## 6. FRONTEND COMPONENTS - STUBS

### FlowView.tsx - Visual Only
❌ **Lines 42, 49, 55**
```typescript
// TODO: Call API to save graph
// TODO: Call validation API
// TODO: Call run API
```

**Impact**: Graph editor displays but can't save, validate, or execute

### Runs.tsx - Empty Page
❌ **Line 5**
```typescript
<p className="text-gray-500">TODO: List all import runs with status</p>
```

**Impact**: Users can't see import history

### QuickStart.tsx - No Post-Action
❌ **Line 51**
```typescript
// TODO: Navigate to graph editor or show success message
```

**Impact**: After instantiating template, user doesn't know what happened

### What Needs to Be Done
1. Wire up FlowView to call `graphsApi.update()`, `validate()`, `run()`
2. Implement Runs page with `runsApi.list()` and status display
3. Add redirect/notification after template instantiation

---

## 7. ERROR LOGGING - SILENT FAILURES

### What You Asked For
Track errors during imports for debugging

### What's BROKEN
❌ **Line `backend/app/importers/executor.py:82`**
```python
# TODO: Log error to RunLog
```

### Impact
- Errors during import are **NOT LOGGED** to database
- Users can't see what went wrong
- No audit trail

### What Needs to Be Done
1. Create RunLog entry when exception occurs
2. Store error message, stack trace, row data
3. Link to Run record

---

## COMPLETION CHECKLIST

### Core Features You Asked For
- [ ] Graph execution actually executes (not just validates)
- [ ] Template progress shows real completion data
- [ ] AI assistant uses MCP tools (or is clearly labeled as keyword matching)
- [ ] Rollback functionality works end-to-end
- [ ] Async execution for imports (at minimum thread-based)
- [ ] FlowView can save/validate/run graphs
- [ ] Runs page lists import history
- [ ] Error logging captures failures

### Current Status
- **0 out of 8 complete**
- All have partial implementations
- All have TODO markers in critical sections

---

## IMPLEMENTATION PRIORITY

### Must Fix (Blockers)
1. **Graph execution** - Core feature, completely non-functional
2. **Template progress** - Returns fake data, misleading users
3. **Rollback** - Critical for fixing mistakes

### Should Fix (Quality)
4. **Async execution** - Prevents timeouts on large imports
5. **FlowView wiring** - Makes UI functional
6. **Runs page** - Essential for monitoring
7. **Error logging** - Debugging imports

### Nice to Have
8. **MCP integration** - Already works in VSCode, web is optional

---

## NEXT STEPS

I will now implement fixes for items 1-7 in order, validating each one works before moving to the next.

No new features. Just finish what you asked for.
