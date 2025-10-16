"""
Inline task runner implementation.

Lean stack implementation using direct execution or threading.
Easy migration path to Celery for distributed execution.
"""
import uuid
from typing import Any, Callable, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future
from app.ports.tasks import TaskRunner, TaskStatus


class InlineTaskRunner(TaskRunner):
    """
    Inline/threaded task execution.

    Modes:
    - inline: Execute immediately in current thread (default)
    - thread: Execute in background thread pool
    """

    def __init__(self, mode: str = "inline", max_workers: int = 4):
        """
        Initialize task runner.

        Args:
            mode: Execution mode ("inline" or "thread")
            max_workers: Max thread pool workers (only for thread mode)
        """
        self.mode = mode
        self.executor = (
            ThreadPoolExecutor(max_workers=max_workers) if mode == "thread" else None
        )
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Submit a task for execution."""
        task_id = task_id or str(uuid.uuid4())

        if self.mode == "inline":
            # Execute immediately
            try:
                result = func(*args, **kwargs)
                self._tasks[task_id] = {
                    "status": TaskStatus.COMPLETED,
                    "result": result,
                    "error": None,
                }
            except Exception as e:
                self._tasks[task_id] = {
                    "status": TaskStatus.FAILED,
                    "result": None,
                    "error": str(e),
                }
        else:
            # Execute in thread pool
            self._tasks[task_id] = {
                "status": TaskStatus.RUNNING,
                "result": None,
                "error": None,
                "future": None,
            }

            def _wrapper():
                try:
                    result = func(*args, **kwargs)
                    self._tasks[task_id]["status"] = TaskStatus.COMPLETED
                    self._tasks[task_id]["result"] = result
                    return result
                except Exception as e:
                    self._tasks[task_id]["status"] = TaskStatus.FAILED
                    self._tasks[task_id]["error"] = str(e)
                    raise

            future = self.executor.submit(_wrapper)
            self._tasks[task_id]["future"] = future

        return task_id

    def status(self, task_id: str) -> TaskStatus:
        """Get task status."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")

        return self._tasks[task_id]["status"]

    def result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Get task result (blocking)."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self._tasks[task_id]

        if task["status"] == TaskStatus.FAILED:
            raise RuntimeError(f"Task failed: {task['error']}")

        if task["status"] == TaskStatus.COMPLETED:
            return task["result"]

        # Wait for completion (thread mode only)
        if self.mode == "thread" and "future" in task:
            future: Future = task["future"]
            try:
                return future.result(timeout=timeout)
            except Exception as e:
                raise RuntimeError(f"Task failed: {e}")

        # For inline mode, should already be completed
        return task["result"]

    def shutdown(self):
        """Shutdown executor (cleanup)."""
        if self.executor:
            self.executor.shutdown(wait=True)
