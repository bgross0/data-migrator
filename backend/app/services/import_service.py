from sqlalchemy.orm import Session
from app.models import Run, Dataset
from app.schemas.run import RunCreate
from app.models.run import RunStatus


class ImportService:
    def __init__(self, db: Session):
        self.db = db

    async def create_run(self, dataset_id: int, run_data: RunCreate):
        """Create a new import run."""
        run = Run(
            dataset_id=dataset_id,
            graph_id=run_data.graph_id,
            status=RunStatus.PENDING,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        # TODO: Trigger import task asynchronously
        # from app.services.import_tasks import execute_import
        # execute_import.delay(run.id, dry_run=run_data.dry_run)

        return run

    def list_runs(self, skip: int = 0, limit: int = 100):
        """List all runs."""
        return self.db.query(Run).offset(skip).limit(limit).all()

    def get_run(self, run_id: int):
        """Get a run by ID."""
        return self.db.query(Run).filter(Run.id == run_id).first()

    async def rollback_run(self, run_id: int) -> bool:
        """Rollback an import run."""
        # TODO: Implement rollback logic
        # 1. Find all KeyMap entries for this run
        # 2. Delete/archive Odoo records
        # 3. Update run status to ROLLED_BACK
        return False
