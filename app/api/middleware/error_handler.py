"""
Error handling middleware for the API.
"""

import os
import logging
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Get the logger
logger = logging.getLogger("dowse")

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and handle all unhandled exceptions.
    This ensures that all errors are properly logged and a consistent
    error response is returned to the client.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and catch any unhandled exceptions.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler
            
        Returns:
            A response object
        """
        try:
            return await call_next(request)
        except Exception as e:
            # Log the error with traceback for debugging
            logger.error(f"Unhandled exception: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Determine if we should show detailed errors
            debug_mode = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
            
            # Create the error response
            error_response = {
                "status": "error",
                "message": "An internal server error occurred"
            }
            
            # Include more details in debug mode
            if debug_mode:
                error_response["detail"] = str(e)
                error_response["traceback"] = traceback.format_exc().split("\n")
                
            # Return a JSON response with a 500 status code
            return JSONResponse(
                status_code=500,
                content=error_response
            ) 