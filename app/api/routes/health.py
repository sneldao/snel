"""
Health check endpoints for monitoring the API status.
"""

import time
import os
import sys
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

@router.get("/debug/packages")
async def list_packages():
    """
    List installed Python packages for debugging purposes.
    Only available in development and preview environments.
    """
    # Check environment to prevent exposing this in production
    environment = os.environ.get("VERCEL_ENV", os.environ.get("ENVIRONMENT", "development"))
    if environment.lower() == "production":
        return {"error": "Debug endpoints are not available in production"}
    
    # Get installed packages using importlib.metadata instead of pkg_resources
    try:
        import importlib.metadata
        packages = sorted([f"{dist.metadata['Name']}=={dist.version}" 
                          for dist in importlib.metadata.distributions()])
    except ImportError:
        # Fallback for older Python versions
        try:
            import subprocess
            result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
            packages = sorted(result.stdout.strip().split("\n"))
        except Exception as e:
            packages = [f"Error listing packages: {str(e)}"]
    
    # Return package list
    return {
        "environment": environment,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "package_count": len(packages),
        "packages": packages
    } 