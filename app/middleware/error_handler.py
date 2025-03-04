from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
import traceback
import json

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled exception: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create a custom error response
            error_response = {
                "error": str(e),
                "detail": "An unexpected error occurred while processing your request.",
                "type": "server_error"
            }
            
            # Return a JSON response with the error details
            return JSONResponse(
                status_code=500,
                content=error_response
            ) 