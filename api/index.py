from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
from typing import Optional
import logging
import traceback
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
logger.info(f"Added {root_dir} to Python path")
logger.info(f"Current PYTHONPATH: {sys.path}")

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

try:
    # Import your existing API functionality
    logger.info("Attempting to import api.py...")
    from api import app as api_app
    logger.info("Successfully imported api.py")
    
    # Mount your existing API
    app.mount("/", api_app)
    logger.info("Successfully mounted API")

except Exception as init_error:
    error_trace = traceback.format_exc()
    logger.error(f"Failed to initialize API: {str(init_error)}\nTraceback:\n{error_trace}")
    
    # Add error routes
    @app.post("/api/process-command")
    async def process_command(request: Request):
        try:
            # Try to read the request body
            body = await request.json()
            logger.error(f"Command processing failed. Request body: {json.dumps(body)}")
        except Exception:
            body = "Could not parse request body"
            
        error_msg = {
            "detail": "API initialization failed",
            "error": str(init_error),
            "trace": error_trace,
            "request_body": body
        }
        logger.error(f"Command processing failed: {error_msg}")
        return JSONResponse(
            status_code=500,
            content=error_msg
        )

    @app.post("/api/execute-transaction")
    async def execute_transaction(request: Request):
        try:
            # Try to read the request body
            body = await request.json()
            logger.error(f"Transaction execution failed. Request body: {json.dumps(body)}")
        except Exception:
            body = "Could not parse request body"
            
        error_msg = {
            "detail": "API initialization failed",
            "error": str(init_error),
            "trace": error_trace,
            "request_body": body
        }
        logger.error(f"Transaction execution failed: {error_msg}")
        return JSONResponse(
            status_code=500,
            content=error_msg
        )

# Health check endpoint
@app.get("/api/health")
async def health_check():
    try:
        # Import check
        from api import app as api_app
        return {
            "status": "ok",
            "python_path": sys.path,
            "root_dir": root_dir
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        return {
            "status": "error",
            "message": str(e),
            "trace": error_trace,
            "python_path": sys.path,
            "root_dir": root_dir
        }

# Error handler for 500 errors
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    error_trace = traceback.format_exc()
    logger.error(f"Internal server error: {str(exc)}\nTraceback:\n{error_trace}")
    
    try:
        # Try to read the request body
        body = await request.json()
        logger.error(f"Request body: {json.dumps(body)}")
    except Exception:
        body = "Could not parse request body"
        
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "error": str(exc),
            "trace": error_trace,
            "request_body": body
        }
    ) 