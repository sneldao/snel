"""
Global error handlers for consistent error responses across the application.
"""
import logging
from datetime import datetime
from typing import Union

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import SNELException, ErrorCode


logger = logging.getLogger(__name__)


async def snel_exception_handler(request: Request, exc: SNELException) -> JSONResponse:
    """Handle custom SNEL exceptions with structured error responses."""
    
    # Log the error with context
    logger.error(
        f"SNEL Exception: {exc.code.value} - {exc.message}",
        extra={
            "error_code": exc.code.value,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Create structured error response
    error_response = {
        "error": {
            "message": exc.message,
            "code": exc.code.value,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "details": exc.details,
            "suggestions": exc.suggestions
        }
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions with consistent format."""
    
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Map common HTTP status codes to error codes
    error_code_mapping = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.UNSUPPORTED_OPERATION,
        429: ErrorCode.RATE_LIMITED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE
    }
    
    error_code = error_code_mapping.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    error_response = {
        "error": {
            "message": exc.detail,
            "code": error_code.value,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "details": {},
            "suggestions": []
        }
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field information."""
    
    logger.warning(
        f"Validation Error: {len(exc.errors())} validation errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "validation_errors": exc.errors(),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Extract field-specific errors
    field_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    error_response = {
        "error": {
            "message": "Validation failed",
            "code": ErrorCode.INVALID_INPUT.value,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "details": {
                "field_errors": field_errors,
                "error_count": len(field_errors)
            },
            "suggestions": [
                "Check the request format and required fields",
                "Ensure all field types match the expected format"
            ]
        }
    }
    
    return JSONResponse(
        status_code=422,
        content=error_response
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with safe error responses."""
    
    # Log the full exception for debugging
    logger.exception(
        f"Unexpected error: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Don't expose internal error details in production
    from app.config.settings import get_config
    config = get_config()
    
    if config.is_development:
        error_message = f"{type(exc).__name__}: {str(exc)}"
        details = {
            "exception_type": type(exc).__name__,
            "exception_args": list(exc.args) if exc.args else []
        }
    else:
        error_message = "An unexpected error occurred"
        details = {}
    
    error_response = {
        "error": {
            "message": error_message,
            "code": ErrorCode.INTERNAL_ERROR.value,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "details": details,
            "suggestions": [
                "Please try again later",
                "If the problem persists, contact support"
            ]
        }
    }
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI application."""
    
    # Custom SNEL exceptions
    app.add_exception_handler(SNELException, snel_exception_handler)
    
    # FastAPI HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Error handlers registered successfully")
