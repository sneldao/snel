"""
Redis-based caching utility for better performance in serverless environments.
"""

import json
import logging
import os
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Use upstash-redis for serverless environments
from upstash_redis import Redis
from upstash_redis.connectors import HttpConnector

logger = logging.getLogger(__name__)

# Initialize Redis client
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    try:
        redis = Redis(
            url=redis_url, 
            connector=HttpConnector(url=redis_url),
            auto_deserialize=True
        )
        logger.info("Redis cache client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis cache client: {e}")
        redis = None
else:
    logger.warning("REDIS_URL not found in environment variables. Caching disabled.")
    redis = None

# Type variable for function return type
T = TypeVar('T')

def cache_result(
    prefix: str, 
    ttl_seconds: int = 600, 
    max_failures: int = 3,
    failure_ttl_seconds: int = 60
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results in Redis.
    
    Args:
        prefix: Prefix for the cache key
        ttl_seconds: Time-to-live in seconds for cache entries
        max_failures: Maximum number of failures to cache
        failure_ttl_seconds: TTL for failure cache entries
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not redis:
                # If Redis is not available, just call the function
                return await func(*args, **kwargs)
            
            # Combine args and kwargs into a single dictionary for the cache key
            key_parts = [prefix]
            
            # Add args to key
            if args:
                key_parts.extend([str(arg) for arg in args])
            
            # Add kwargs to key (sorted by key for consistency)
            if kwargs:
                for k, v in sorted(kwargs.items()):
                    # Convert dictionaries to strings for cache key
                    if isinstance(v, dict):
                        v = json.dumps(v, sort_keys=True)
                    key_parts.append(f"{k}={v}")
            
            # Build the final cache key
            cache_key = f"{':'.join(key_parts)}"
            
            # Try to get from cache
            try:
                cached_data = await redis.get(cache_key)
                if cached_data is not None:
                    # Check if it's a failure marker
                    if isinstance(cached_data, dict) and cached_data.get("__failure_count"):
                        logger.warning(f"Found failure marker in cache: {cache_key}")
                        # If failure count is less than max, try the function again
                        if cached_data["__failure_count"] < max_failures:
                            logger.info(f"Retrying after {cached_data['__failure_count']} failures")
                            try:
                                result = await func(*args, **kwargs)
                                # Cache the successful result
                                await redis.set(cache_key, result, ex=ttl_seconds)
                                return result
                            except Exception as e:
                                # Increment the failure count
                                failure_data = {
                                    "__failure_count": cached_data["__failure_count"] + 1,
                                    "__last_error": str(e)
                                }
                                await redis.set(cache_key, failure_data, ex=failure_ttl_seconds)
                                raise
                        else:
                            # Max failures reached, return the last error
                            logger.error(f"Max failures reached for {cache_key}: {cached_data.get('__last_error')}")
                            raise Exception(f"Service temporarily unavailable: {cached_data.get('__last_error')}")
                    else:
                        # Return cached successful result
                        logger.debug(f"Cache hit for {cache_key}")
                        return cast(T, cached_data)
            except Exception as e:
                # If there's an error with Redis, log it and continue
                logger.error(f"Error retrieving from cache: {e}")
            
            # Cache miss or Redis error, call the function
            try:
                result = await func(*args, **kwargs)
                
                # Cache the result
                try:
                    await redis.set(cache_key, result, ex=ttl_seconds)
                except Exception as cache_error:
                    logger.error(f"Error caching result: {cache_error}")
                
                return result
            except Exception as e:
                # Cache the failure for a shorter time
                try:
                    failure_data = {
                        "__failure_count": 1,
                        "__last_error": str(e)
                    }
                    await redis.set(cache_key, failure_data, ex=failure_ttl_seconds)
                except Exception as cache_error:
                    logger.error(f"Error caching failure: {cache_error}")
                
                # Re-raise the original error
                raise
        
        return wrapper
    
    return decorator 