from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from redis import Redis
from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint - verifies database and Redis connectivity."""
    health_status = {
        "status": "healthy",
        "database": "disconnected",
        "redis": "disconnected",
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        health_status["redis"] = "connected"
        redis_client.close()
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"error: {str(e)}"

    return health_status
