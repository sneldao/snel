"""
Health check endpoints for monitoring the API status.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse

health_router = APIRouter(tags=["health"])

@health_router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Simple health check endpoint to verify the API is working.
    """
    return JSONResponse(
        content={
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@health_router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic health checks.
    """
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@health_router.get("/api/health")
async def api_health():
    """
    API-specific health check endpoint.
    """
    return JSONResponse(
        content={
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "api": True
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

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