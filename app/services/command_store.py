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
        # Always normalize to lowercase for consistency
        normalized_id = user_id.lower()
        logger.info(f"Normalized user ID from {user_id} to {normalized_id}")
        return f"pending_command:{normalized_id}"
    
    def store_command(self, user_id: str, command: str, chain_id: int) -> None:
        """Store a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Storing command with key: {key}, command: {command}, chain_id: {chain_id}")
        
        try:
            all_keys = self._redis.keys("pending_command:*")
            logger.info(f"All existing keys before storing: {all_keys}")
            
            # Store the command with additional metadata
            command_data = {
                "command": command,
                "chain_id": chain_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "user_id": user_id,  # Store the user_id for reference
                "status": "pending"  # Add a status field
            }
            
            # Serialize the command data
            serialized_data = json.dumps(command_data)
            logger.info(f"Storing command data: {serialized_data}")
            
            self._redis.set(
                key,
                serialized_data,
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
            logger.error(f"Error storing command: {e}", exc_info=True)
    
    def get_command(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Getting command with key: {key}")
        
        try:
            all_keys = self._redis.keys("pending_command:*")
            logger.info(f"All existing keys when retrieving: {all_keys}")
            
            # First try the exact key
            value = self._redis.get(key)
            if value:
                logger.info(f"Found command for key {key}: {value}")
                try:
                    return json.loads(value)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing command data for key {key}: {e}")
                    return None
            
            # If not found, try case-insensitive matching
            for existing_key in all_keys:
                if existing_key.lower() == key.lower():
                    value = self._redis.get(existing_key)
                    if value:
                        logger.info(f"Found command with case-insensitive match for key {existing_key}: {value}")
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing command data for key {existing_key}: {e}")
                            continue
            
            # If still not found, try prefix matching
            user_id_part = user_id.lower()
            for existing_key in all_keys:
                existing_user_id = existing_key.split(":", 1)[1].lower() if ":" in existing_key else ""
                if existing_user_id and (existing_user_id.startswith(user_id_part) or user_id_part.startswith(existing_user_id)):
                    logger.info(f"Found command with user ID prefix match: {existing_key}")
                    value = self._redis.get(existing_key)
                    if value:
                        logger.info(f"Found command with user ID prefix match for key {existing_key}: {value}")
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing command data for key {existing_key}: {e}")
                            continue
            
            # If we get here, no command was found
            logger.info(f"No command found for user ID: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting command: {e}", exc_info=True)
            return None
    
    def clear_command(self, user_id: str) -> None:
        """Clear a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Clearing command with key: {key}")
        self._redis.delete(key)
    
    def list_all_commands(self) -> List[Dict[str, Any]]:
        """List all pending commands."""
        keys = self._redis.keys("pending_command:*")
        if not keys:
            return []
        
        logger.info(f"Found {len(keys)} pending commands: {keys}")
        
        values = self._redis.mget(*keys)
        commands = []
        for key, value in zip(keys, values):
            if value:
                try:
                    command_data = json.loads(value)
                    user_id = key.split(":", 1)[1]
                    command_data["user_id"] = user_id
                    command_data["key"] = key
                    commands.append(command_data)
                    logger.info(f"Command for key {key}: {command_data}")
                except Exception as e:
                    logger.error(f"Error parsing command data for key {key}: {e}")
        return commands 