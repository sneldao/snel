import json
import datetime
import logging
from typing import Dict, Optional, List, Any
from urllib.parse import urlparse
from upstash_redis import Redis
import os

logger = logging.getLogger(__name__)

class RedisService:
    """Redis service for storing and retrieving data."""
    
    def __init__(self):
        # Initialize Redis client from environment variables
        redis_url = os.getenv("REDIS_URL")
        upstash_url = os.getenv("UPSTASH_REDIS_REST_URL")
        upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        # Validate connection parameters
        if not ((redis_url and isinstance(redis_url, str)) or 
                (upstash_url and upstash_token and isinstance(upstash_url, str) and isinstance(upstash_token, str))):
            raise ValueError("Either REDIS_URL or both UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are required")

        # Initialize Redis client
        if upstash_url and upstash_token and isinstance(upstash_url, str) and isinstance(upstash_token, str):
            self._redis = Redis(url=upstash_url, token=upstash_token)
        elif redis_url and isinstance(redis_url, str):
            parsed = urlparse(redis_url)
            rest_url = f"https://{parsed.hostname}"
            token = parsed.password
            self._redis = Redis(url=rest_url, token=token)
        else:
            raise ValueError("No valid Redis connection parameters found")

        self._ttl = 1800  # 30 minutes default TTL
    
    def normalize_key(self, key: str) -> str:
        """Normalize a key for consistent storage."""
        if key.startswith("0x"):
            return key.lower()
        return key.lower()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis with optional TTL."""
        normalized_key = self.normalize_key(key)
        return self._redis.set(normalized_key, value, ex=ttl or self._ttl)
    
    def get(self, key: str) -> Any:
        """Get a value from Redis."""
        normalized_key = self.normalize_key(key)
        return self._redis.get(normalized_key)
    
    def delete(self, key: str) -> bool:
        """Delete a value from Redis."""
        normalized_key = self.normalize_key(key)
        return self._redis.delete(normalized_key)
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching a pattern."""
        return self._redis.keys(pattern)
    
    def mget(self, *keys: str) -> List[Any]:
        """Get multiple values from Redis."""
        normalized_keys = [self.normalize_key(key) for key in keys]
        return self._redis.mget(*normalized_keys)
    
    def test_connection(self) -> bool:
        """Test the Redis connection."""
        try:
            test_key = "connection_test"
            self.set(test_key, "test")
            result = self.get(test_key)
            self.delete(test_key)
            return result == "test"
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            return False 