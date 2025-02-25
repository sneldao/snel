from fastapi import APIRouter, Depends
import datetime
import sys
import os
import logging
from app.services.redis_service import RedisService
from app.api.dependencies import get_redis_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/health")
async def health_check(redis_service: RedisService = Depends(get_redis_service)):
    """Health check endpoint."""
    try:
        # Check Redis connection
        redis_status = "unknown"
        redis_error = None
        try:
            redis_connected = redis_service.test_connection()
            redis_status = "connected" if redis_connected else "error"
            if not redis_connected:
                redis_error = "Redis connection test failed"
        except Exception as e:
            redis_status = "error"
            redis_error = str(e)
            logger.error(f"Redis health check failed: {e}")

        # Check environment variables
        env_vars = {
            "REDIS_URL": os.environ.get("REDIS_URL") and isinstance(os.environ.get("REDIS_URL"), str),
            "UPSTASH_REDIS_REST_URL": os.environ.get("UPSTASH_REDIS_REST_URL") and isinstance(os.environ.get("UPSTASH_REDIS_REST_URL"), str),
            "UPSTASH_REDIS_REST_TOKEN": os.environ.get("UPSTASH_REDIS_REST_TOKEN") and isinstance(os.environ.get("UPSTASH_REDIS_REST_TOKEN"), str),
            "MORALIS_API_KEY": bool(os.environ.get("MORALIS_API_KEY")),
            "ALCHEMY_KEY": bool(os.environ.get("ALCHEMY_KEY")),
            "COINGECKO_API_KEY": bool(os.environ.get("COINGECKO_API_KEY")),
        }
        
        return {
            "status": "healthy" if redis_status == "connected" else "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "services": {
                "redis": {
                    "status": redis_status,
                    "error": redis_error
                }
            },
            "environment": {
                "python_version": sys.version,
                "environment_variables": env_vars
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 