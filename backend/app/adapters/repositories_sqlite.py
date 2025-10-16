"""
SQLite implementations of repository interfaces.

Lean stack implementation using SQLAlchemy + SQLite.
Easy migration path to Postgres (same SQLAlchemy API).
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session
import polars as pl
from app.ports.repositories import ExceptionsRepo, DatasetsRepo
from app.models import Exception, Dataset


class SQLiteExceptionsRepo(ExceptionsRepo):
    """SQLite implementation of ExceptionsRepo."""

    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        dataset_id: int,
        model: str,
        row_ptr: str,
        error_code: str,
        hint: str,
        offending: Dict[str, Any],
    ) -> int:
        """Add a new exception record."""
        exception = Exception(
            dataset_id=dataset_id,
            model=model,
            row_ptr=row_ptr,
            error_code=error_code,
            hint=hint,
            offending=offending,
        )
        self.db.add(exception)
        self.db.flush()  # Get ID without committing
        return exception.id

    def list(
        self, dataset_id: int, model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List exceptions for a dataset."""
        query = self.db.query(Exception).filter(Exception.dataset_id == dataset_id)

        if model:
            query = query.filter(Exception.model == model)

        exceptions = query.order_by(Exception.created_at.desc()).all()

        return [
            {
                "id": exc.id,
                "dataset_id": exc.dataset_id,
                "model": exc.model,
                "row_ptr": exc.row_ptr,
                "error_code": exc.error_code,
                "hint": exc.hint,
                "offending": exc.offending,
                "created_at": exc.created_at.isoformat(),
            }
            for exc in exceptions
        ]

    def clear(self, dataset_id: int, model: Optional[str] = None) -> int:
        """Clear exceptions for a dataset."""
        query = self.db.query(Exception).filter(Exception.dataset_id == dataset_id)

        if model:
            query = query.filter(Exception.model == model)

        count = query.delete()
        self.db.flush()
        return count

    def count(self, dataset_id: int, model: Optional[str] = None) -> int:
        """Count exceptions for a dataset."""
        query = self.db.query(Exception).filter(Exception.dataset_id == dataset_id)

        if model:
            query = query.filter(Exception.model == model)

        return query.count()


class SQLiteDatasetsRepo(DatasetsRepo):
    """SQLite implementation of DatasetsRepo."""

    def __init__(self, db: Session):
        self.db = db

    def get_dataframe(
        self, dataset_id: int, sheet_name: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Get DataFrame for a dataset.

        Prefers cleaned data if available, falls back to raw data.
        """
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Determine which file to use
        if dataset.cleaned_file_path and Path(dataset.cleaned_file_path).exists():
            file_path = Path(dataset.cleaned_file_path)
        elif dataset.source_file and dataset.source_file.path:
            file_path = Path(dataset.source_file.path)
        else:
            raise ValueError(f"Dataset {dataset_id} has no data file available")

        # Load data based on file type
        if file_path.suffix.lower() in [".csv"] or ".csv" in file_path.name:
            return pl.read_csv(file_path)
        elif file_path.suffix.lower() in [".xlsx", ".xls"] or any(
            ext in file_path.name for ext in [".xlsx", ".xls"]
        ):
            # For Excel, read specific sheet if provided
            if sheet_name:
                try:
                    return pl.read_excel(file_path, sheet_name=sheet_name)
                except Exception:
                    # Fallback to pandas
                    import pandas as pd

                    pandas_df = pd.read_excel(file_path, sheet_name=sheet_name)
                    return pl.from_pandas(pandas_df)
            else:
                # Read first sheet
                try:
                    sheets = pl.read_excel(file_path, sheet_id=0)
                    return sheets
                except Exception:
                    # Fallback to pandas
                    import pandas as pd

                    pandas_df = pd.read_excel(file_path)
                    return pl.from_pandas(pandas_df)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    def put_artifact(self, dataset_id: int, name: str, path: str) -> None:
        """Store artifact metadata for a dataset."""
        # For lean stack, we just store in filesystem
        # In future, could track in database table
        pass

    def get_artifact_path(self, dataset_id: int, name: str) -> Optional[str]:
        """Get artifact path by name."""
        # For lean stack, construct path from ARTIFACT_ROOT
        from app.core.config import settings

        artifact_root = Path(getattr(settings, "ARTIFACT_ROOT", "./out"))
        artifact_path = artifact_root / str(dataset_id) / name

        if artifact_path.exists():
            return str(artifact_path)

        return None
