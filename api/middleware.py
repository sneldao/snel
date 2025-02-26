"""
Middleware for handling common serverless deployment issues.
"""

import os
import sys
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import contextmanager
import traceback

# Setup logging
logger = logging.getLogger("api.middleware")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class ServerlessCompatibilityMiddleware(BaseHTTPMiddleware):
    """Middleware for handling common serverless deployment issues."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            # Call the next middleware/route handler
            response = await call_next(request)
            return response
        except OSError as e:
            # Catch file system errors
            if "Read-only file system" in str(e):
                logger.error(f"Read-only file system error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Server error: Unable to write to file system",
                        "error_type": "read_only_fs",
                        "error": str(e)
                    }
                )
            # Re-raise other OS errors
            raise
        except Exception as e:
            # Log all other exceptions
            logger.error(f"Unhandled exception: {e}")
            logger.error(traceback.format_exc())
            raise

def add_serverless_compatibility(app: FastAPI) -> FastAPI:
    """
    Add serverless compatibility middleware to a FastAPI app.
    
    Args:
        app: The FastAPI application
        
    Returns:
        The app with serverless compatibility middleware added
    """
    app.add_middleware(ServerlessCompatibilityMiddleware)
    
    # Log middleware addition
    logger.info("Added serverless compatibility middleware")
    
    return app 