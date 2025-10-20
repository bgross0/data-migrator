"""
Celery tasks for executing imports and graph execution.
"""
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Run
from app.models.run import RunStatus
from app.models.graph import Graph, GraphRun
from app.connectors.odoo import OdooConnector
from app.services.import_service import ImportService
from app.services.graph_execute_service import GraphExecuteService
from app.schemas.graph import GraphSpec
from app.core.config import settings


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

        dataset_id = run.dataset_id

        # Initialize Odoo connector
        odoo = OdooConnector(
            url=settings.ODOO_URL,
            db=settings.ODOO_DB,
            username=settings.ODOO_USERNAME,
            password=settings.ODOO_PASSWORD
        )
        odoo.authenticate()

        # Execute import via ImportService
        import_service = ImportService(db)

        # Run the import (this updates the run object with results)
        result_run = import_service.execute_import(
            dataset_id=dataset_id,
            odoo=odoo,
            dry_run=dry_run
        )

        return {
            "status": result_run.status.value,
            "run_id": run_id,
            "stats": result_run.stats
        }

    except Exception as e:
        # ImportService handles run status updates, but catch any unexpected errors
        return {"error": str(e), "run_id": run_id}
    finally:
        db.close()
