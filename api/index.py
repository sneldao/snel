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

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

# CRITICAL: Create a fake dowse.logger module BEFORE importing anything else
# This prevents the 'Read-only file system' error in serverless environments
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
import types
mock_logger = MockLogger()
mock_logger_module = types.ModuleType("dowse.logger")
mock_logger_module.get_logger = lambda name=None: MockLogger(name if name else "dowse")
mock_logger_module.logger = mock_logger  # Add the logger attribute

# Insert it into sys.modules
sys.modules["dowse.logger"] = mock_logger_module

logger.info("Dowse logger monkey patched for serverless environment")

# Now it's safe to import the app modules
try:
    # Import routes
    from app.api.routes.messaging_router import router as messaging_router
    from app.api.routes.swap_router import router as swap_router
    from app.api.routes.wallet_router import router as wallet_router
    from app.api.routes.commands_router import router as commands_router
    from app.api.routes.brian_router import router as brian_router
    from app.api.routes.dca_router import router as dca_router
    from app.api.routes.health import router as health_router
except ImportError as e:
    logger.error(f"Error importing routes: {e}")
    logger.error(traceback.format_exc())
    raise

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