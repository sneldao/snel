"""
Health check endpoints using the new dependency injection system.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.dependencies import (
    get_service_container, 
    check_brian_service, 
    check_redis_service,
    ServiceContainer
)
from app.config.settings import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    environment: str
    services: Dict[str, bool] = {}
    details: Dict[str, Any] = {}


@router.get("/", response_model=HealthResponse)
async def health_check(
    service: str = Query("", description="Specific service to check (portfolio, brian, redis)"),
    container: ServiceContainer = Depends(get_service_container),
    settings: Settings = Depends(get_settings)
) -> HealthResponse:
    """
    Comprehensive health check endpoint.
    
    Args:
        service: Optional specific service to check
        container: Service container dependency
        settings: Application settings
    """
    timestamp = datetime.utcnow().isoformat()
    
    response = HealthResponse(
        status="healthy",
        timestamp=timestamp,
        environment=settings.environment
    )
    
    if service:
        # Check specific service
        service_status = await _check_specific_service(service, container)
        response.services[service] = service_status
        response.details[f"{service}_available"] = str(service_status)
        
        if not service_status:
            response.status = "unhealthy"
    else:
        # Check all services
        services_status = await _check_all_services(container)
        response.services = services_status
        
        # Overall status based on critical services
        critical_services = ["brian"]  # Redis is optional in development
        if settings.is_production:
            critical_services.append("redis")
        
        unhealthy_critical = [
            service for service in critical_services 
            if not services_status.get(service, False)
        ]
        
        if unhealthy_critical:
            response.status = "unhealthy"
            response.details["unhealthy_critical_services"] = unhealthy_critical
    
    return response


@router.get("/ready")
async def readiness_check(
    container: ServiceContainer = Depends(get_service_container),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Kubernetes-style readiness probe.
    Returns 200 if the service is ready to accept traffic.
    """
    try:
        # Check critical services
        brian_ok = await check_brian_service(container)
        
        if not brian_ok:
            return {"ready": False, "reason": "Brian API not available"}
        
        # In production, also check Redis
        if settings.is_production:
            redis_ok = await check_redis_service(container)
            if not redis_ok:
                return {"ready": False, "reason": "Redis not available"}
        
        return {"ready": True}
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False, "reason": str(e)}


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes-style liveness probe.
    Returns 200 if the service is alive (basic health).
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


async def _check_specific_service(service_name: str, container: ServiceContainer) -> bool:
    """Check a specific service availability."""
    try:
        if service_name == "portfolio":
            # Check if we can access portfolio services
            try:
                from app.services.portfolio.portfolio_service import Web3Helper
                web3_helper = Web3Helper(supported_chains={
                    1: "Ethereum",
                    8453: "Base",
                    42161: "Arbitrum",
                    10: "Optimism",
                    137: "Polygon"
                })
                return len(web3_helper.web3_instances) > 0
            except Exception:
                return False
        
        elif service_name == "brian":
            return await check_brian_service(container)
        
        elif service_name == "redis":
            return await check_redis_service(container)
        
        elif service_name == "exa":
            try:
                exa_client = container.get_exa_client()
                return exa_client is not None
            except Exception:
                return False
        
        elif service_name == "firecrawl":
            try:
                firecrawl_client = container.get_firecrawl_client()
                return firecrawl_client is not None
            except Exception:
                return False
        
        else:
            logger.warning(f"Unknown service requested: {service_name}")
            return False
    
    except Exception as e:
        logger.error(f"Error checking {service_name} service: {e}")
        return False


async def _check_all_services(container: ServiceContainer) -> Dict[str, bool]:
    """Check all available services."""
    services = {}
    
    # Core services
    services["brian"] = await check_brian_service(container)
    services["redis"] = await check_redis_service(container)
    
    # Optional services (don't fail if not configured)
    try:
        container.get_exa_client()
        services["exa"] = True
    except Exception:
        services["exa"] = False
    
    try:
        container.get_firecrawl_client()
        services["firecrawl"] = True
    except Exception:
        services["firecrawl"] = False
    
    # Portfolio service
    try:
        from app.services.portfolio.portfolio_service import Web3Helper
        web3_helper = Web3Helper(supported_chains={
            1: "Ethereum",
            8453: "Base",
            42161: "Arbitrum",
            10: "Optimism",
            137: "Polygon"
        })
        services["portfolio"] = len(web3_helper.web3_instances) > 0
    except Exception:
        services["portfolio"] = False
    
    return services
