"""
Vercel handler for the Pointless API.
This file is the entry point for the Vercel serverless function.
"""

import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from datetime import datetime

# Setup paths
root_dir = str(Path(__file__).parent.parent)
api_dir = str(Path(__file__).parent)

# Add paths to Python path
sys.path.insert(0, root_dir)  # Root directory first
sys.path.insert(0, api_dir)   # API directory second

# Import our patches module which will automatically apply the patches
from api.patches import patch_dowse_modules

# Apply the patches for Vercel deployment
patch_dowse_modules()

# Configure logging
logger = logging.getLogger("dowse")

# Fix circular import issues by ensuring proper import order
try:
    # Import the models first to ensure they're loaded
    from app.models.telegram import TelegramMessage, TelegramWebhookRequest
    
    # Import dependencies in a specific order to avoid circular imports
    from app.services.redis_service import RedisService
    from app.services.token_service import TokenService
    from app.services.wallet_service import WalletService
    
    # Now import the main app
    from app.main import app
    
    # Add CORS middleware first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"]
    )
    
    # Add error handling middleware
    class ErrorHandlerMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            try:
                response = await call_next(request)
                return response
            except Exception as e:
                logger.exception("Error handling request")
                return JSONResponse(
                    status_code=500,
                    content={"detail": str(e)}
                )
    
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "timestamp": str(datetime.now())}
    
    @app.get("/api/health")
    async def api_health_check():
        return {"status": "ok", "timestamp": str(datetime.now())}
    
except Exception as e:
    logger.error(f"Error importing modules: {e}")
    logger.exception("Full traceback:")
    raise

# Create handler for Vercel
async def handler(request, context):
    return await app(request, context) 