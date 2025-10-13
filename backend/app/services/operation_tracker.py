"""
Operation Tracker - Real-time progress tracking for long-running operations.

Uses SQLite to store operation progress that frontend can poll.
"""
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime
from typing import Dict, List, Optional
import uuid
from app.core.config import settings
from pathlib import Path

Base = declarative_base()


class Operation(Base):
    """Stores operation progress in SQLite."""
    __tablename__ = "operations"

    id = Column(String, primary_key=True)
    operation_type = Column(String, nullable=False)  # 'upload', 'mapping', 'split', etc.
    dataset_id = Column(Integer, nullable=True)
    status = Column(String, nullable=False)  # 'running', 'complete', 'error'
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    current_step = Column(String, nullable=True)
    steps = Column(JSON, nullable=False)  # List of step objects
    result = Column(JSON, nullable=True)  # Final result data
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create SQLite engine for operations (separate from main DB)
operations_db_path = Path(settings.STORAGE_PATH) / "operations.db"
operations_db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{operations_db_path}", echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


class OperationTracker:
    """
    Tracks progress of long-running operations.

    Usage:
        tracker = OperationTracker.create("upload", dataset_id=123, steps=[...])
        tracker.update_step("step1", "in_progress", "Uploading file...")
        tracker.set_progress(25.0)
        tracker.update_step("step1", "complete")
        tracker.complete(result={"dataset_id": 123})
    """

    def __init__(self, operation_id: str, db: Session):
        self.operation_id = operation_id
        self.db = db
        self._operation = None

    @classmethod
    def create(
        cls,
        operation_type: str,
        steps: List[Dict],
        dataset_id: Optional[int] = None
    ) -> "OperationTracker":
        """
        Create a new operation tracker.

        Args:
            operation_type: Type of operation ('upload', 'mapping', 'split', etc.)
            steps: List of step definitions, e.g.:
                [
                    {"id": "step1", "label": "Uploading file", "status": "pending"},
                    {"id": "step2", "label": "Profiling", "status": "pending"},
                ]
            dataset_id: Optional dataset ID this operation belongs to

        Returns:
            OperationTracker instance
        """
        operation_id = str(uuid.uuid4())
        db = SessionLocal()

        operation = Operation(
            id=operation_id,
            operation_type=operation_type,
            dataset_id=dataset_id,
            status="running",
            progress=0.0,
            steps=steps
        )
        db.add(operation)
        db.commit()

        tracker = cls(operation_id, db)
        tracker._operation = operation
        return tracker

    @classmethod
    def get(cls, operation_id: str) -> Optional["OperationTracker"]:
        """Get existing operation tracker."""
        db = SessionLocal()
        operation = db.query(Operation).filter(Operation.id == operation_id).first()
        if not operation:
            db.close()
            return None

        tracker = cls(operation_id, db)
        tracker._operation = operation
        return tracker

    def _load_operation(self):
        """Load operation from database."""
        if not self._operation:
            self._operation = self.db.query(Operation).filter(
                Operation.id == self.operation_id
            ).first()
        return self._operation

    def update_step(
        self,
        step_id: str,
        status: str,
        detail: Optional[str] = None
    ):
        """
        Update a specific step's status.

        Args:
            step_id: ID of the step to update
            status: New status ('pending', 'in_progress', 'complete', 'error')
            detail: Optional detail text to show under the step
        """
        operation = self._load_operation()
        if not operation:
            return

        steps = operation.steps.copy()
        for step in steps:
            if step["id"] == step_id:
                step["status"] = status
                if detail:
                    step["detail"] = detail
                if status == "in_progress":
                    operation.current_step = step["label"]
                break

        operation.steps = steps
        operation.updated_at = datetime.utcnow()
        self.db.commit()

    def set_progress(self, progress: float):
        """
        Set overall progress percentage.

        Args:
            progress: Progress from 0.0 to 100.0
        """
        operation = self._load_operation()
        if not operation:
            return

        operation.progress = min(100.0, max(0.0, progress))
        operation.updated_at = datetime.utcnow()
        self.db.commit()

    def complete(self, result: Optional[Dict] = None):
        """
        Mark operation as complete.

        Args:
            result: Optional result data to store
        """
        operation = self._load_operation()
        if not operation:
            return

        # Mark all steps as complete
        steps = operation.steps.copy()
        for step in steps:
            if step["status"] != "error":
                step["status"] = "complete"

        operation.steps = steps
        operation.status = "complete"
        operation.progress = 100.0
        operation.result = result
        operation.updated_at = datetime.utcnow()
        self.db.commit()

    def error(self, error_message: str, step_id: Optional[str] = None):
        """
        Mark operation as failed.

        Args:
            error_message: Error message
            step_id: Optional step ID that failed
        """
        operation = self._load_operation()
        if not operation:
            return

        # Mark step as error if specified
        if step_id:
            steps = operation.steps.copy()
            for step in steps:
                if step["id"] == step_id:
                    step["status"] = "error"
                    step["detail"] = error_message
                    break
            operation.steps = steps

        operation.status = "error"
        operation.error = error_message
        operation.updated_at = datetime.utcnow()
        self.db.commit()

    def get_status(self) -> Dict:
        """
        Get current operation status.

        Returns:
            Dict with operation status, progress, steps, etc.
        """
        operation = self._load_operation()
        if not operation:
            return {"error": "Operation not found"}

        return {
            "id": operation.id,
            "operation_type": operation.operation_type,
            "dataset_id": operation.dataset_id,
            "status": operation.status,
            "progress": operation.progress,
            "current_step": operation.current_step,
            "steps": operation.steps,
            "result": operation.result,
            "error": operation.error,
            "created_at": operation.created_at.isoformat() if operation.created_at else None,
            "updated_at": operation.updated_at.isoformat() if operation.updated_at else None,
        }

    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
