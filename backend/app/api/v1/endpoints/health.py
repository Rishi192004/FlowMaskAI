"""
Health-check endpoint.
GET /api/v1/health

Returns the application status and database connectivity.
Used by Docker health checks and load balancers.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str           # "ok" | "degraded"
    version: str
    app_env: str
    database: str         # "connected" | "unreachable"


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> HealthResponse:
    """
    Returns application health status.
    - `status`: overall health ("ok" if all systems operational, else "degraded")
    - `database`: "connected" if PostgreSQL is reachable
    """
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        database="connected" if db_ok else "unreachable",
    )
