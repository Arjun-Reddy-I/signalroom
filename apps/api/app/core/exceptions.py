import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorEnvelope(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="User-safe human-readable message")
    details: Any | None = Field(None, description="Validation errors or additional details")
    request_id: str = Field(..., description="Traceable request ID")


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Requested resource not found", code: str = "NOT_FOUND"):
        super().__init__(code=code, message=message, status_code=status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication credentials required or invalid", code: str = "UNAUTHORIZED"):
        super().__init__(code=code, message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to access this resource", code: str = "FORBIDDEN"):
        super().__init__(code=code, message=message, status_code=status.HTTP_403_FORBIDDEN)


class BadRequestException(AppException):
    def __init__(self, message: str = "Invalid request payload or parameters", code: str = "BAD_REQUEST", details: Any | None = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource state conflict", code: str = "CONFLICT"):
        super().__init__(code=code, message=message, status_code=status.HTTP_409_CONFLICT)


async def app_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppException):
        exc = AppException(code="INTERNAL_SERVER_ERROR", message="An unexpected server error occurred.")
    request_id = getattr(request.state, "request_id", "unknown")
    envelope = ErrorEnvelope(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        exc = RequestValidationError(errors=[{"loc": [], "msg": "Invalid request", "type": "value_error"}])
    request_id = getattr(request.state, "request_id", "unknown")
    details = exc.errors()
    envelope = ErrorEnvelope(
        code="VALIDATION_ERROR",
        message="Request payload validation failed",
        details=details,
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=envelope.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled exception on request {request_id}: {exc}", exc_info=True)
    envelope = ErrorEnvelope(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
        details=None,
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=envelope.model_dump())
