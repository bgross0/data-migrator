"""
Celery tasks for profiling datasets.
"""
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Dataset, Sheet, ColumnProfile
from app.core.profiler import ColumnProfiler


@celery_app.task(name="profile_dataset")
def profile_dataset(dataset_id: int):
    """
    Profile a dataset - analyze all sheets and columns.

    Args:
        dataset_id: ID of dataset to profile
    """
    db = SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return {"error": "Dataset not found"}

        # Profile the file
        profiler = ColumnProfiler(dataset.source_file.path)
        profiles = profiler.profile()

        # Store results in database
        for sheet_name, columns in profiles.items():
            sheet = Sheet(
                dataset_id=dataset.id,
                name=sheet_name,
                n_rows=columns[0].get("n_rows", 0) if columns else 0,
                n_cols=len(columns),
            )
            db.add(sheet)
            db.flush()

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
                db.add(col_profile)

        db.commit()
        return {"status": "completed", "dataset_id": dataset_id}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
