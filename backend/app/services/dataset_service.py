from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models import SourceFile, Dataset, Sheet, ColumnProfile
from app.core.config import settings
from app.core.profiler import ColumnProfiler
from app.services.operation_tracker import OperationTracker
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import polars as pl


class DatasetService:
    def __init__(self, db: Session):
        self.db = db

    async def create_from_upload(self, file: UploadFile, name: str = None) -> Tuple[Dataset, str]:
        """Create a dataset from an uploaded file and return operation ID for tracking."""

        # Create operation tracker
        file_size_mb = f"{file.size / 1024 / 1024:.2f} MB" if file.size else "unknown size"
        tracker = OperationTracker.create(
            operation_type="upload",
            steps=[
                {"id": "upload", "label": "Uploading file", "status": "in_progress", "detail": file_size_mb},
                {"id": "save", "label": "Saving to storage", "status": "pending"},
                {"id": "db_create", "label": "Creating database records", "status": "pending"},
                {"id": "profile", "label": "Profiling columns", "status": "pending", "detail": "Detecting types and patterns"},
                {"id": "finalize", "label": "Finalizing", "status": "pending"},
            ]
        )
        operation_id = tracker.operation_id

        try:
            # Step 1: Upload file (already done by FastAPI, just mark complete)
            tracker.set_progress(10)
            tracker.update_step("upload", "complete")

            # Step 2: Save file to storage
            tracker.update_step("save", "in_progress", "Writing file to disk")
            tracker.set_progress(15)

            storage_path = Path(settings.STORAGE_PATH) / "uploads"
            storage_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"
            file_path = storage_path / filename

            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            tracker.update_step("save", "complete")
            tracker.set_progress(20)

            # Step 3: Create database records
            tracker.update_step("db_create", "in_progress", "Creating SourceFile and Dataset")

            source_file = SourceFile(
                path=str(file_path),
                mime_type=file.content_type,
                original_filename=file.filename,
            )
            self.db.add(source_file)
            self.db.commit()
            self.db.refresh(source_file)

            dataset_name = name or f"Dataset from {file.filename}"
            dataset = Dataset(
                name=dataset_name,
                source_file_id=source_file.id,
            )
            self.db.add(dataset)
            self.db.commit()
            self.db.refresh(dataset)

            tracker.update_step("db_create", "complete")
            tracker.set_progress(30)

            # Update tracker with dataset ID
            tracker._load_operation().dataset_id = dataset.id
            tracker.db.commit()

            # Step 4: Profile columns
            dataset.profiling_status = "processing"
            self.db.commit()

            tracker.update_step("profile", "in_progress", "Analyzing column types and patterns")
            tracker.set_progress(40)

            profiler = ColumnProfiler(str(file_path))
            profiles = profiler.profile()

            tracker.set_progress(80)
            tracker.update_step("profile", "complete")

            # Step 5: Finalize - Store column profiles
            tracker.update_step("finalize", "in_progress", "Creating column profiles")

            for sheet_name, columns in profiles.items():
                sheet = Sheet(
                    dataset_id=dataset.id,
                    name=sheet_name,
                    n_rows=columns[0].get("n_rows", 0) if columns else 0,
                    n_cols=len(columns),
                )
                self.db.add(sheet)
                self.db.flush()

                for col_data in columns:
                    col_profile = ColumnProfile(
                        sheet_id=sheet.id,
                        name=col_data["name"],
                        dtype_guess=col_data["dtype"],
                        null_pct=col_data["null_pct"],
                        distinct_pct=col_data["distinct_pct"],
                        patterns=col_data.get("patterns"),
                        sample_values=col_data.get("sample_values"),
                    )
                    self.db.add(col_profile)

            dataset.profiling_status = "complete"
            self.db.commit()

            tracker.update_step("finalize", "complete")
            tracker.set_progress(100)
            tracker.complete(result={"dataset_id": dataset.id})

        except Exception as e:
            # Mark operation as error
            tracker.error(str(e), "profile" if "profile" in str(e).lower() else None)

            # Mark dataset as failed
            dataset.profiling_status = "failed"
            self.db.commit()
            print(f"Upload error: {e}")
            raise
        finally:
            tracker.close()

        self.db.refresh(dataset)
        return dataset, operation_id

    def _save_cleaned_data(self, original_path: Path, cleaned_data: Dict) -> Path:
        """
        Save cleaned data to disk alongside original file using Polars.

        Args:
            original_path: Path to original uploaded file
            cleaned_data: Dict of {sheet_name: DataFrame} with cleaned data

        Returns:
            Path to saved cleaned file
        """
        # Create cleaned filename (e.g., file.csv -> file.cleaned.csv)
        cleaned_path = original_path.with_suffix(f'.cleaned{original_path.suffix}')

        # Save based on file type
        if original_path.suffix.lower() == '.csv':
            # Single sheet for CSV
            if 'Sheet1' in cleaned_data:
                cleaned_data['Sheet1'].write_csv(cleaned_path)
        else:
            # Multiple sheets for Excel - write each sheet separately
            # Note: Polars write_excel can handle multiple sheets
            with pl.ExcelWriter(cleaned_path) as writer:
                for sheet_name, df in cleaned_data.items():
                    df.write_excel(writer, worksheet=sheet_name)

        return cleaned_path

    def list_datasets(self, skip: int = 0, limit: int = 100):
        """List all datasets."""
        return self.db.query(Dataset).offset(skip).limit(limit).all()

    def get_dataset(self, dataset_id: int):
        """Get a dataset by ID."""
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def delete_dataset(self, dataset_id: int) -> bool:
        """Delete a dataset."""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return False
        self.db.delete(dataset)
        self.db.commit()
        return True
