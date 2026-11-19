"""
FlowMind FastAPI application entry point.

Responsibilities:
  - Create and configure the FastAPI application instance
  - Register middleware (CORS, correlation-ID injection)
  - Register routers
  - Register exception handlers
  - Configure structured logging on startup
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, request_id_ctx, setup_logging

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "FlowMind — Process Mining & Operational Analytics Platform. "
            "Analyzes business event logs, reconstructs actual workflows, "
            "detects deviations, and provides evidence-based recommendations."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Correlation-ID middleware ──────────────────────────
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        token = request_id_ctx.set(req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        request_id_ctx.reset(token)
        return response

    # ── Startup / Shutdown ────────────────────────────────
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "FlowMind API starting",
            extra={"version": settings.APP_VERSION, "env": settings.APP_ENV},
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("FlowMind API shutting down")

    # ── Routers ───────────────────────────────────────────
    app.include_router(api_router)
    # Also mount /api/datasets, /api/analytics, /api/process, /api/conformance, /api/ai directly
    from app.api.v1.endpoints import ai, analytics, conformance, datasets, process
    app.include_router(datasets.router, prefix="/api")
    app.include_router(analytics.router, prefix="/api")
    app.include_router(process.router, prefix="/api")
    app.include_router(conformance.router, prefix="/api")
    app.include_router(ai.router, prefix="/api")

    # ── Exception handlers ────────────────────────────────
    register_exception_handlers(app)

    return app


app = create_app()
