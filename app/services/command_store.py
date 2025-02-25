import json
import datetime
import logging
from typing import Dict, Optional, List, Any
from .redis_service import RedisService

logger = logging.getLogger(__name__)

class CommandStore:
    """Store for pending commands using Redis."""
    
    def __init__(self, redis_service: RedisService):
        self._redis = redis_service
        self._ttl = 1800  # 30 minutes
    
    def _make_key(self, user_id: str) -> str:
        """Create a Redis key for a user's pending command."""
        normalized_id = self._redis.normalize_key(user_id)
        logger.info(f"Normalized user ID from {user_id} to {normalized_id}")
        return f"pending_command:{normalized_id}"
    
    def store_command(self, user_id: str, command: str, chain_id: int) -> None:
        """Store a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Storing command with key: {key}, command: {command}, chain_id: {chain_id}")
        
        try:
            all_keys = self._redis.keys("pending_command:*")
            logger.info(f"All existing keys before storing: {all_keys}")
            
            self._redis.set(
                key,
                json.dumps({
                    "command": command,
                    "chain_id": chain_id,
                    "timestamp": datetime.datetime.now().isoformat()
                }),
                self._ttl
            )
            logger.info(f"Command stored successfully for key: {key}")
            
            # Verify storage
            value = self._redis.get(key)
            if value:
                logger.info(f"Verified command storage: {value}")
            else:
                logger.error(f"Failed to verify command storage for key: {key}")
        except Exception as e:
            logger.error(f"Error storing command: {e}")
    
    def get_command(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Getting command with key: {key}")
        
        try:
            all_keys = self._redis.keys("pending_command:*")
            logger.info(f"All existing keys when retrieving: {all_keys}")
            
            value = self._redis.get(key)
            if value:
                logger.info(f"Found command for key {key}: {value}")
                return json.loads(value)
            else:
                logger.info(f"No command found for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Error getting command: {e}")
            return None
    
    def clear_command(self, user_id: str) -> None:
        """Clear a pending command for a user."""
        key = self._make_key(user_id)
        self._redis.delete(key)
    
    def list_all_commands(self) -> List[Dict[str, Any]]:
        """List all pending commands."""
        keys = self._redis.keys("pending_command:*")
        if not keys:
            return []
        
        values = self._redis.mget(*keys)
        commands = []
        for key, value in zip(keys, values):
            if value:
                command_data = json.loads(value)
                command_data["user_id"] = key.split(":", 1)[1]
                commands.append(command_data)
        return commands 