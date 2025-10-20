"""
Shared task runner singleton for background task execution.

Provides a module-level singleton instance of InlineTaskRunner
that is shared across all requests for efficiency.
"""
from typing import Optional
import atexit
from app.adapters.tasks_inline import InlineTaskRunner

# Module-level singleton instance
_task_runner: Optional[InlineTaskRunner] = None
_task_runner_lock = None

def get_task_runner() -> InlineTaskRunner:
    """
    Get the shared task runner singleton instance.

    Creates the instance on first call and reuses it for all subsequent calls.
    The runner is automatically shut down on application exit.

    Returns:
        InlineTaskRunner: Shared task runner instance in thread mode
    """
    global _task_runner
    if _task_runner is None:
        _task_runner = InlineTaskRunner(mode="thread", max_workers=4)
        # Register cleanup on application shutdown
        atexit.register(shutdown_task_runner)
    return _task_runner


def shutdown_task_runner():
    """
    Shutdown the task runner and clean up resources.

    This is automatically called on application exit but can also
    be called manually for graceful shutdown.
    """
    global _task_runner
    if _task_runner is not None:
        _task_runner.shutdown()
        _task_runner = None


# Alternative using FastAPI background tasks (if preferred over threads)
from fastapi import BackgroundTasks

def run_graph_export_background(
    background_tasks: BackgroundTasks,
    db_session,
    dataset_id: int,
    graph_id: int,
    run_id: str
):
    """
    Alternative implementation using FastAPI's built-in background tasks.

    This is another option that doesn't require managing a thread pool.

    Args:
        background_tasks: FastAPI BackgroundTasks instance
        db_session: Database session
        dataset_id: Dataset to export
        graph_id: Graph defining the export
        run_id: Run ID to update
    """
    from app.services.graph_execute_service import GraphExecuteService

    def execute():
        execute_service = GraphExecuteService(db_session)
        execute_service.execute_graph_export(
            dataset_id=dataset_id,
            graph_id=graph_id,
            run_id=run_id
        )

    background_tasks.add_task(execute)