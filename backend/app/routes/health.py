"""
app/routes/health.py
─────────────────────
Lightweight health-check endpoints used by load balancers, Docker HEALTHCHECK,
and monitoring systems.

GET /health        → liveness probe  (is the process running?)
GET /health/ready  → readiness probe (can it serve traffic?)
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", include_in_schema=False)
async def liveness() -> dict:
    """Simple liveness probe — returns 200 if the process is alive."""
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@router.get("/health/ready", include_in_schema=False)
async def readiness(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Readiness probe — verifies the database connection is healthy.
    Returns 200 if ready, 503 if not (FastAPI will propagate the exception).
    """
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
