from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models import SourceFile, Dataset, Sheet, ColumnProfile
from app.core.config import settings
from app.core.profiler import ColumnProfiler
import os
from datetime import datetime
from pathlib import Path
from typing import Dict
import pandas as pd


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

        # Profile and clean the file
        try:
            dataset.profiling_status = "processing"
            self.db.commit()

            # Enable data cleaning during profiling
            profiler = ColumnProfiler(str(file_path), clean_data=True)
            result = profiler.profile()

            # Extract results
            profiles = result["profiles"]
            cleaned_data = result.get("cleaned_data", {})
            cleaning_report = result.get("cleaning_report", {})
            column_mappings = result.get("column_mappings", {})

            # Save cleaned data to disk
            if cleaned_data:
                cleaned_file_path = self._save_cleaned_data(file_path, cleaned_data)
                dataset.cleaned_file_path = str(cleaned_file_path)

            # Store cleaning report in dataset
            dataset.cleaning_report = cleaning_report

            # Store column profiles in database
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
        except Exception as e:
            # If profiling fails, mark as failed and log error
            dataset.profiling_status = "failed"
            self.db.commit()
            print(f"Profiling error: {e}")
            raise

        self.db.refresh(dataset)
        return dataset

    def _save_cleaned_data(self, original_path: Path, cleaned_data: Dict) -> Path:
        """
        Save cleaned data to disk alongside original file.

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
                cleaned_data['Sheet1'].to_csv(cleaned_path, index=False)
        else:
            # Multiple sheets for Excel
            with pd.ExcelWriter(cleaned_path, engine='openpyxl') as writer:
                for sheet_name, df in cleaned_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

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
