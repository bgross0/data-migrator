"""
Celery tasks for executing imports.
"""
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Run
from app.models.run import RunStatus
from app.connectors.odoo import OdooConnector
from app.importers.executor import TwoPhaseImporter


@celery_app.task(name="execute_import")
def execute_import(run_id: int, dry_run: bool = True):
    """
    Execute an import run.

    Args:
        run_id: ID of run to execute
        dry_run: If True, validate but don't write to Odoo
    """
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {"error": "Run not found"}

        # Update status
        run.status = RunStatus.IMPORTING
        db.commit()

        # TODO: Get prepared data from dataset/mappings
        # TODO: Get import graph
        # TODO: Execute import
        # For now, just mark as completed
        run.status = RunStatus.COMPLETED
        run.stats = {"created": 0, "updated": 0, "errors": 0}
        db.commit()

        return {"status": "completed", "run_id": run_id}

    except Exception as e:
        run.status = RunStatus.FAILED
        db.commit()
        return {"error": str(e)}
    finally:
        db.close()
