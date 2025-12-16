"""
Dependency injection system for clean service management.
Eliminates import chaos and provides consistent service access.
"""
import logging
from typing import Optional

from fastapi import Depends

from app.config.settings import Settings, get_settings
from app.core.exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Central container for all application services.
    Implements dependency injection pattern to eliminate import chaos.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._brian_client: Optional[object] = None
        self._command_processor: Optional[object] = None
        self._redis_client: Optional[object] = None
        self._privacy_service: Optional[object] = None

        # Validate required services can be initialized
        self._validate_service_requirements()
    
    def _validate_service_requirements(self):
        """Validate that required external services are properly configured."""
        if self.settings.is_production:
            if not self.settings.external_services.brian_api_key:
                raise ConfigurationError(
                    "Brian API key is required in production",
                    setting_name="BRIAN_API_KEY"
                )
    
    @property
    def brian_client(self):
        """Get Brian API client (lazy initialization)."""
        if self._brian_client is None:
            try:
                from app.services.brian.client import brian_client
                # Use the existing global brian_client instance
                self._brian_client = brian_client
                logger.info("Brian client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Brian client: {e}")
                raise ConfigurationError(
                    "Failed to initialize Brian API client",
                    suggestions=["Check BRIAN_API_KEY configuration"]
                )
        return self._brian_client
    
    @property
    def command_processor(self):
        """Get command processor (lazy initialization)."""
        if self._command_processor is None:
            try:
                from app.services.command_processor import CommandProcessor
                # Initialize transaction flow service first to avoid circular dependency
                transaction_flow_service = None
                try:
                    from app.services.transaction_flow_service import TransactionFlowService
                    transaction_flow_service = TransactionFlowService()
                except Exception as tfs_error:
                    logger.warning(f"Transaction flow service initialization failed: {tfs_error}")

                self._command_processor = CommandProcessor(
                    brian_client=self.brian_client,
                    settings=self.settings,
                    transaction_flow_service=transaction_flow_service
                )
                logger.info("Command processor initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize command processor: {e}")
                raise ConfigurationError(
                    "Failed to initialize command processor",
                    suggestions=["Check service dependencies"]
                )
        return self._command_processor



    @property
    def redis_client(self):
        """Get Redis client (lazy initialization)."""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.from_url(
                    self.settings.database.redis_url,
                    db=self.settings.database.redis_db,
                    max_connections=self.settings.database.redis_max_connections,
                    decode_responses=True
                )
                # Test connection
                self._redis_client.ping()
                logger.info("Redis client initialized successfully")
            except Exception as e:
                logger.warning(f"Redis client initialization failed: {e}")
                # Redis is optional in development
                if self.settings.is_production:
                    raise ConfigurationError(
                        "Redis connection failed in production",
                        setting_name="REDIS_URL",
                        suggestions=["Check Redis server availability and connection string"]
                    )
                self._redis_client = None
        return self._redis_client

    @property
    def privacy_service(self):
        """Get privacy service (lazy initialization)."""
        if self._privacy_service is None:
            try:
                from app.services.privacy_service import PrivacyService
                from app.core.config_manager import config_manager
                
                self._privacy_service = PrivacyService(config_manager)
                logger.info("Privacy service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize privacy service: {e}")
                raise ConfigurationError(
                    "Failed to initialize privacy service",
                    suggestions=["Check chain privacy configurations"]
                )
        return self._privacy_service
    
    def get_exa_client(self):
        """Get Exa API client (on-demand initialization)."""
        if not self.settings.external_services.exa_api_key:
            raise ConfigurationError(
                "Exa API key not configured",
                setting_name="EXA_API_KEY"
            )
        
        try:
            from app.services.external.exa_service import ExaClient
            return ExaClient(
                api_key=self.settings.external_services.exa_api_key,
                base_url=self.settings.external_services.exa_api_url,
                timeout=self.settings.api.timeout
            )
        except Exception as e:
            logger.error(f"Failed to initialize Exa client: {e}")
            raise ConfigurationError(
                "Failed to initialize Exa API client",
                suggestions=["Check EXA_API_KEY configuration"]
            )
    
    def get_firecrawl_client(self):
        """Get Firecrawl API client (on-demand initialization)."""
        if not self.settings.external_services.firecrawl_api_key:
            raise ConfigurationError(
                "Firecrawl API key not configured",
                setting_name="FIRECRAWL_API_KEY"
            )
        
        try:
            from app.services.external.firecrawl_service import FirecrawlClient
            return FirecrawlClient(
                api_key=self.settings.external_services.firecrawl_api_key,
                base_url=self.settings.external_services.firecrawl_api_url,
                timeout=self.settings.api.timeout
            )
        except Exception as e:
            logger.error(f"Failed to initialize Firecrawl client: {e}")
            raise ConfigurationError(
                "Failed to initialize Firecrawl API client",
                suggestions=["Check FIRECRAWL_API_KEY configuration"]
            )
    
    async def close(self):
        """Clean up resources when shutting down."""
        if self._redis_client:
            try:
                # Redis client close is synchronous, not async
                self._redis_client.close()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")

        # Close other clients if they have cleanup methods
        if hasattr(self._brian_client, 'close'):
            try:
                if hasattr(self._brian_client.close, '__call__'):
                    # Check if close method is async
                    import inspect
                    if inspect.iscoroutinefunction(self._brian_client.close):
                        await self._brian_client.close()
                    else:
                        self._brian_client.close()
                logger.info("Brian client closed")
            except Exception as e:
                logger.error(f"Error closing Brian client: {e}")


# Global container instance
_service_container: Optional[ServiceContainer] = None

def get_service_container(settings: Settings = Depends(get_settings)) -> ServiceContainer:
    """
    Get the service container (singleton).
    This ensures we only create one container instance per application lifecycle.
    """
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer(settings)
    return _service_container


# Convenience dependency functions for common services
def get_brian_client(container: ServiceContainer = Depends(get_service_container)):
    """Get Brian API client dependency."""
    return container.brian_client


def get_command_processor(container: ServiceContainer = Depends(get_service_container)):
    """Get command processor dependency."""
    return container.command_processor


def get_redis_client(container: ServiceContainer = Depends(get_service_container)):
    """Get Redis client dependency (optional)."""
    return container.redis_client


def get_settings_dependency() -> Settings:
    """Get settings dependency."""
    return get_settings()


# Health check dependencies
async def check_brian_service(container: ServiceContainer = Depends(get_service_container)) -> bool:
    """Check if Brian API service is available."""
    try:
        # Simple health check - try to access the client
        client = container.brian_client
        return client is not None
    except Exception:
        return False


async def check_redis_service(container: ServiceContainer = Depends(get_service_container)) -> bool:
    """Check if Redis service is available."""
    try:
        redis_client = container.redis_client
        if redis_client:
            redis_client.ping()
            return True
        return False
    except Exception:
        return False
