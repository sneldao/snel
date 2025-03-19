"""
Health check endpoints for monitoring the API status.
"""

import time
import os
import sys
import platform
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

health_router = APIRouter(tags=["health"])

# Model for health check response
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    uptime: float
    environment: str
    platform: str
    python_version: str
    uptime_seconds: float
    vercel: bool
    services: Dict[str, bool]

# Track startup time
START_TIME = datetime.now()

# API version
VERSION = "1.0.0"

@health_router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Health check endpoint to verify the API is working.
    
    This endpoint returns information about the runtime environment
    and checks if essential services are available.
    """
    try:
        # Get uptime
        uptime = (datetime.now() - START_TIME).total_seconds()
        
        # Check if Redis is available
        redis_available = False
        try:
            from app.services.redis_service import get_redis_service
            redis = get_redis_service()
            await redis.ping()
            redis_available = True
        except Exception:
            pass
        
        # Check if we're running on Vercel
        is_vercel = os.environ.get("VERCEL", "0") == "1"
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "platform": platform.platform(),
            "python_version": sys.version,
            "uptime_seconds": uptime,
            "vercel": is_vercel,
            "services": {
                "redis": redis_available,
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "platform": platform.platform(),
            "python_version": sys.version,
            "uptime_seconds": (datetime.now() - START_TIME).total_seconds(),
            "vercel": os.environ.get("VERCEL", "0") == "1",
            "services": {
                "redis": False,
            },
            "error": str(e)
        }

@health_router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic health checks.
    """
    return {"status": "ok", "timestamp": time.time()}

@health_router.get("/debug/packages")
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