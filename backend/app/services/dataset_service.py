from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models import SourceFile, Dataset, Sheet, ColumnProfile
from app.core.config import settings
from app.core.profiler import ColumnProfiler
import os
from datetime import datetime
from pathlib import Path


class DatasetService:
    def __init__(self, db: Session):
        self.db = db

    async def create_from_upload(self, file: UploadFile, name: str = None) -> Dataset:
        """Create a dataset from an uploaded file."""
        # Save file to storage
        storage_path = Path(settings.STORAGE_PATH) / "uploads"
        storage_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = storage_path / filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Create SourceFile record
        source_file = SourceFile(
            path=str(file_path),
            mime_type=file.content_type,
            original_filename=file.filename,
        )
        self.db.add(source_file)
        self.db.commit()
        self.db.refresh(source_file)

        # Create Dataset record
        dataset_name = name or f"Dataset from {file.filename}"
        dataset = Dataset(
            name=dataset_name,
            source_file_id=source_file.id,
        )
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)

        # Profile the file immediately (synchronous for now)
        try:
            profiler = ColumnProfiler(str(file_path))
            profiles = profiler.profile()

            # Store results in database
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

            self.db.commit()
        except Exception as e:
            # If profiling fails, log but don't fail the upload
            print(f"Profiling error: {e}")

        self.db.refresh(dataset)
        return dataset

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
