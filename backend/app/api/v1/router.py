"""
Central v1 API router. All endpoint routers are registered here.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    conformance,
    datasets,
    health,
    process,
    projects,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(datasets.router)
api_router.include_router(analytics.router)
api_router.include_router(process.router)
api_router.include_router(conformance.router)
