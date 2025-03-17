"""
Entry point for Vercel deployment.
This file is used by Vercel to run the application.
"""

import sys
import os
from pathlib import Path
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
from typing import Dict, Any

# Setup paths
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_dir = os.path.dirname(os.path.abspath(__file__))

# Add paths to Python path
sys.path.insert(0, root_dir)  # Root directory first
sys.path.insert(0, api_dir)   # API directory second

# CRITICAL: Monkey patch Dowse's logging module BEFORE importing anything else
# This prevents the 'Read-only file system' error in serverless environments
def patch_dowse_modules():
    """
    Patch Dowse's logger module before it gets imported to prevent file system access.
    Must be called before any imports that might trigger Dowse's logger initialization.
    """
    import importlib.util
    import types
    import logging
    
    # Create a default logger that only writes to stdout
    logger = logging.getLogger("dowse")
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add a stdout handler only
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    # Create a fake logger module to replace dowse.logger
    # This prevents dowse from creating file handlers
    class MockLogger:
        def __init__(self, name="dowse"):
            self.name = name
            self.logger = logging.getLogger(name)
        
        def info(self, msg, *args, **kwargs):
            self.logger.info(msg, *args, **kwargs)
        
        def warning(self, msg, *args, **kwargs):
            self.logger.warning(msg, *args, **kwargs)
        
        def error(self, msg, *args, **kwargs):
            self.logger.error(msg, *args, **kwargs)
        
        def debug(self, msg, *args, **kwargs):
            self.logger.debug(msg, *args, **kwargs)
        
        def critical(self, msg, *args, **kwargs):
            self.logger.critical(msg, *args, **kwargs)
        
        def exception(self, msg, *args, **kwargs):
            self.logger.exception(msg, *args, **kwargs)
    
    # Create a fake dowse.logger module
    mock_logger = MockLogger()
    mock_logger_module = types.ModuleType("dowse.logger")
    mock_logger_module.get_logger = lambda name=None: MockLogger(name if name else "dowse")
    
    # Insert it into sys.modules
    sys.modules["dowse.logger"] = mock_logger_module

# Apply the patch
patch_dowse_modules()

# Now it's safe to import the app 

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import routes
from app.api.routes.messaging_router import router as messaging_router
from app.api.routes.swap_router import router as swap_router
from app.api.routes.wallet_router import router as wallet_router
from app.api.routes.commands_router import router as commands_router
from app.api.routes.brian_router import router as brian_router
from app.api.routes.dca_router import router as dca_router
from app.api.routes.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Snel API",
    description="API for Snel, a lazy AI agent assistant",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://snel-pointless.vercel.app",
        "https://snel-pointless-git-main-papas-projects-5b188431.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(messaging_router, prefix="/api/messaging")
app.include_router(swap_router, prefix="/api/swap")
app.include_router(wallet_router, prefix="/api/wallet")
app.include_router(commands_router, prefix="/api/commands")
app.include_router(brian_router, prefix="/api/brian")
app.include_router(dca_router, prefix="/api/dca")
app.include_router(health_router, prefix="/api/health")

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "type": str(type(exc).__name__),
            "message": str(exc),
        },
    ) 