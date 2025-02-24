from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import your existing API functionality
    from api import app as api_app
    
    # Create the ASGI app
    app = FastAPI()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount your existing API
    app.mount("/", api_app)

    # Health check endpoint
    @app.get("/api/health")
    async def health_check():
        return {"status": "ok"}

    # Error handler for 500 errors
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception):
        logger.error(f"Internal server error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."}
        )

except Exception as e:
    logger.error(f"Failed to initialize API: {str(e)}", exc_info=True)
    # Create a minimal app that returns error responses
    app = FastAPI()
    
    @app.get("/api/health")
    async def health_check():
        return {"status": "error", "message": str(e)}
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path: str):
        raise HTTPException(status_code=500, detail="API initialization failed") 