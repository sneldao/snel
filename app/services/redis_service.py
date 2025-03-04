import json
import datetime
import logging
from datetime import timezone
from typing import Dict, Optional, List, Any
from urllib.parse import urlparse
import os
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import Depends
import redis.asyncio

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        return obj.isoformat() if isinstance(obj, datetime) else super().default(obj)

class SwapConfirmationState(BaseModel):
    """Model for storing swap confirmation state."""
    wallet_address: str
    chain_id: int
    command: str
    step: str  # "token_confirmation" or "quote_selection"
    token_in: Dict[str, Any]
    token_out: Dict[str, Any]
    amount: float
    timestamp: datetime
    selected_quote: Optional[Dict[str, Any]] = None

class RedisService(BaseModel):
    """Service for interacting with Redis."""
    redis_url: str
    client: Optional[Any] = None
    expire_time: int = 1800  # 30 minutes default expiration
    is_upstash: bool = Field(default=False)  # Add is_upstash to class definition
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, **data):
        super().__init__(**data)

        # Determine whether to use Upstash or local Redis
        self.is_upstash = "upstash" in self.redis_url.lower()

        if self.is_upstash:
            # For Upstash, parse the URL to extract credentials
            try:
                # Parse the Redis URL (format: rediss://default:password@hostname:port)
                # It seems Upstash Redis connection strings use 'rediss://'
                url_parts = urlparse(self.redis_url)
                hostname = url_parts.hostname
                port = url_parts.port or 6379
                password = url_parts.password

                # Import Upstash Redis
                from upstash_redis import Redis

                # Extract the token from the password
                token = password.split('@')[0] if password and '@' in password else password
                # Create the client with the extracted parameters
                self.client = Redis(url=f"https://{hostname}", token=token)
                logger.info("Using Upstash Redis client")
            except ImportError:
                logger.warning("upstash_redis not installed, falling back to redis.asyncio")
                self.client = redis.asyncio.from_url(self.redis_url, decode_responses=True)
                self.is_upstash = False
            except Exception as e:
                logger.error(f"Error initializing Upstash Redis: {e}")
                logger.warning("Falling back to redis.asyncio")
                self.client = redis.asyncio.from_url(self.redis_url, decode_responses=True)
                self.is_upstash = False
        else:
            # For local Redis, use redis.asyncio
            self.client = redis.asyncio.from_url(self.redis_url, decode_responses=True)

        logger.info(f"Redis client initialized with URL: {self.redis_url[:10]}... (Upstash: {self.is_upstash})")

    def normalize_key(self, key: str) -> str:
        """Normalize a key for consistent storage.
        
        Always converts to lowercase for consistency.
        """
        # Always convert to lowercase for consistency
        normalized = key.lower()
        logger.debug(f"Normalized key from '{key}' to '{normalized}'")
        return normalized
    
    def get_swap_confirmation_key(self, wallet_address: str) -> str:
        """Generate a key for storing swap confirmation state."""
        return f"swap_confirmation:{wallet_address.lower()}"

    async def store_swap_confirmation(
        self,
        wallet_address: str,
        chain_id: int,
        command: str,
        step: str,
        token_in: Dict[str, Any],
        token_out: Dict[str, Any],
        amount: float,
        selected_quote: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store swap confirmation state in Redis."""
        try:
            key = self.get_swap_confirmation_key(wallet_address)
            state = SwapConfirmationState(
                wallet_address=wallet_address,
                chain_id=chain_id,
                command=command,
                step=step,
                token_in=token_in,
                token_out=token_out,
                amount=amount,
                timestamp=datetime.now(timezone.utc),
                selected_quote=selected_quote,
            )
            await self.set(key, state.model_dump(), expire=300)  # Expire after 5 minutes
            return True
        except Exception as e:
            logger.error(f"Error storing swap confirmation: {e}")
            return False

    async def get_swap_confirmation(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """Get swap confirmation state from Redis."""
        try:
            key = self.get_swap_confirmation_key(wallet_address)
            state = await self.get(key)
            if state:
                # Convert timestamp back to datetime if needed
                if isinstance(state.get("timestamp"), str):
                    state["timestamp"] = datetime.fromisoformat(state["timestamp"])
            return state
        except Exception as e:
            logger.error(f"Error getting swap confirmation: {e}")
            return None

    async def clear_swap_confirmation(self, wallet_address: str) -> bool:
        """Clear swap confirmation state from Redis."""
        try:
            key = self.get_swap_confirmation_key(wallet_address)
            await self.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error clearing swap confirmation: {e}")
            return False

    async def update_swap_confirmation(
        self,
        wallet_address: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update existing swap confirmation state."""
        try:
            state = await self.get_swap_confirmation(wallet_address)
            if state:
                state.update(updates)
                key = self.get_swap_confirmation_key(wallet_address)
                await self.set(key, state, expire=300)  # Reset expiration to 5 minutes
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating swap confirmation: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        try:
            value = self.client.get(key) if self.is_upstash else await self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a value in Redis with optional expiration in seconds."""
        try:
            # Convert value to JSON string using custom encoder
            json_value = json.dumps(value, cls=DateTimeEncoder)

            if self.is_upstash:
                # Upstash Redis
                if expire:
                    self.client.setex(key, expire, json_value)
                else:
                    self.client.set(key, json_value)
            elif expire:
                await self.client.setex(key, expire, json_value)
            else:
                await self.client.set(key, json_value)

            return True
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            if self.is_upstash:
                self.client.delete(key)
            else:
                await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            if self.is_upstash:
                return bool(self.client.exists(key))
            else:
                return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Error checking if key {key} exists in Redis: {e}")
            return False

    async def close(self):
        """Close the Redis connection."""
        if self.client:
            await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def keys(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern."""
        try:
            if self.is_upstash:
                return self.client.keys(pattern)
            else:
                return await self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys with pattern {pattern}: {e}")
            return []
    
    async def mget(self, *keys: str) -> List[Any]:
        """Get multiple values from Redis."""
        try:
            if self.is_upstash:
                return self.client.mget(*keys)
            else:
                return await self.client.mget(*keys)
        except Exception as e:
            logger.error(f"Error running mget on keys {keys}: {e}")
            return [None] * len(keys)
    
    async def test_connection(self) -> bool:
        """Test the Redis connection."""
        try:
            test_key = "connection_test"
            await self.set(test_key, "test")
            result = await self.get(test_key)
            await self.delete(test_key)
            return result == "test"
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            return False

    async def set_pending_command(self, wallet_address: str, command: str) -> None:
        """Store a pending command for a wallet address."""
        key = f"pending_command:{wallet_address}"
        if self.is_upstash:
            self.client.set(key, command, ex=self.expire_time)
        else:
            await self.client.set(key, command, ex=self.expire_time)

    async def get_pending_command(self, wallet_address: str) -> Optional[str]:
        """Get the pending command for a wallet address."""
        key = f"pending_command:{wallet_address}"
        return self.client.get(key) if self.is_upstash else await self.client.get(key)

    async def clear_pending_command(self, wallet_address: str) -> None:
        """Clear the pending command for a wallet address."""
        key = f"pending_command:{wallet_address}"
        if self.is_upstash:
            self.client.delete(key)
        else:
            await self.client.delete(key)
    
    async def store_token_data(self, wallet_address: str, token_data: Dict[str, Any]) -> None:
        """Store token data for a wallet address."""
        key = f"token_data:{wallet_address}"
        json_data = json.dumps(token_data)
        if self.is_upstash:
            self.client.set(key, json_data, ex=self.expire_time)
        else:
            await self.client.set(key, json_data, ex=self.expire_time)

    async def get_token_data(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """Get token data for a wallet address."""
        key = f"token_data:{wallet_address}"
        data = self.client.get(key) if self.is_upstash else await self.client.get(key)
        return json.loads(data) if data else None

async def get_redis_service() -> RedisService:
    """Get an instance of RedisService."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return RedisService(redis_url=redis_url) 