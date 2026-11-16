"""
Central v1 API router. All endpoint routers are registered here.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, projects

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
