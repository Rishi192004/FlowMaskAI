"""
Custom exception classes and FastAPI exception handlers.
All unhandled exceptions are mapped to a standard error response schema.
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


# ── Custom Exceptions ─────────────────────────────────────────────────────────

class FlowMindException(Exception):
    """Base exception for all application-level errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, error_code: str | None = None):
        self.message = message
        if error_code:
            self.error_code = error_code
        super().__init__(message)


class NotFoundError(FlowMindException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictError(FlowMindException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class AuthenticationError(FlowMindException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_ERROR"


class AuthorizationError(FlowMindException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_ERROR"


class ValidationError(FlowMindException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"


class DatasetProcessingError(FlowMindException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "DATASET_PROCESSING_ERROR"


# ── Error Response Builder ────────────────────────────────────────────────────

def _error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
) -> JSONResponse:
    req_id = request_id_ctx.get()
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "message": message,
            "request_id": req_id,
        },
    )


# ── Handler Registration ──────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(FlowMindException)
    async def flowmind_exc_handler(
        request: Request, exc: FlowMindException
    ) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("Application error", exc_info=exc)
        return _error_response(
            request, exc.status_code, exc.error_code, exc.message
        )

    @app.exception_handler(Exception)
    async def unhandled_exc_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc)
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please contact support.",
        )
