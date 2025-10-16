"""
Task runner interface.

Ports (interfaces) for lean stack → scale migration path:
- Current: Inline/Thread execution
- Future: Celery distributed tasks

Easy to swap implementations without changing business logic.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRunner(ABC):
    """
    Task execution interface.

    Allows switching between inline, threaded, or distributed (Celery) execution.
    """

    @abstractmethod
    def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Submit a task for execution.

        Args:
            func: Function to execute
            *args: Positional arguments
            task_id: Optional task ID (generated if not provided)
            **kwargs: Keyword arguments

        Returns:
            Task ID for status tracking
        """
        pass

    @abstractmethod
    def status(self, task_id: str) -> TaskStatus:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            TaskStatus enum
        """
        pass

    @abstractmethod
    def result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        Get task result (blocking).

        Args:
            task_id: Task ID
            timeout: Optional timeout in seconds

        Returns:
            Task result

        Raises:
            TimeoutError: If timeout exceeded
            RuntimeError: If task failed
        """
        pass
