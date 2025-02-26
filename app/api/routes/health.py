"""
Health check endpoints for monitoring the API status.
"""

import os
import sys
import time
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(tags=["health"])

# Model for health check response
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: float
    uptime: float
    environment: str
    python_version: str
    services: Dict[str, Any]

# Track startup time
START_TIME = time.time()

# API version
VERSION = "1.0.0"

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API status and dependencies.
    """
    # Check Redis connection
    redis_status = "unknown"
    redis_error = None
    
    try:
        from app.utils.cache import redis
        if redis:
            await redis.ping()
            redis_status = "ok"
        else:
            redis_status = "not_configured"
    except Exception as e:
        redis_status = "error"
        redis_error = str(e)
    
    # Get environment
    environment = os.environ.get("VERCEL_ENV", os.environ.get("ENVIRONMENT", "development"))
    
    # Build response
    return HealthResponse(
        status="ok",
        version=VERSION,
        timestamp=time.time(),
        uptime=time.time() - START_TIME,
        environment=environment,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        services={
            "redis": {
                "status": redis_status,
                "error": redis_error
            }
        }
    )

@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic health checks.
    """
    return {"status": "ok", "timestamp": time.time()} 