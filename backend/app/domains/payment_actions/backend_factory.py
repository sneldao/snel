"""Factory for initializing payment action storage backends."""
import redis.asyncio as redis
from typing import Optional
from app.config.settings import get_settings
from .storage import BaseStorageBackend, InMemoryStorageBackend, RedisStorageBackend, PostgreSQLStorageBackend


async def get_payment_actions_backend() -> BaseStorageBackend:
    """
    Factory function to get configured storage backend.
    
    CLEAN: Single initialization point for all backends.
    MODULAR: Easy to switch backends via configuration.
    """
    settings = get_settings()
    backend_type = settings.database.payment_actions_backend.lower()
    
    if backend_type == "memory":
        return InMemoryStorageBackend()
    
    elif backend_type == "redis":
        # Initialize Redis client
        redis_client = await redis.from_url(
            settings.database.redis_url,
            db=settings.database.redis_db,
            max_connections=settings.database.redis_max_connections,
            decode_responses=True,  # Automatically decode bytes to strings
        )
        return RedisStorageBackend(redis_client)
    
    elif backend_type == "postgresql":
        # TODO: Implement PostgreSQL backend initialization
        # Requires SQLAlchemy async session factory setup
        raise NotImplementedError("PostgreSQL backend not yet configured")
    
    else:
        raise ValueError(f"Unknown payment actions backend: {backend_type}")
