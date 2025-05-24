"""
Chat history service with Redis support.
"""
import json
import os
from typing import List, Dict, Any, Optional
from redis import Redis
from datetime import datetime, timedelta

class ChatHistoryService:
    def __init__(self):
        """Initialize the chat history service with Redis connection."""
        self.memory_store = {}
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.redis = Redis.from_url(redis_url, decode_responses=True)
                # Test the connection
                self.redis.ping()
                self.use_redis = True
            except Exception as e:
                print(f"Redis connection failed: {str(e)}. Using in-memory storage instead.")
                self.use_redis = False
        else:
            self.use_redis = False

    def _get_key(self, wallet_address: Optional[str], user_name: Optional[str]) -> str:
        """Generate a Redis key for the conversation history."""
        return f"chat_history:{wallet_address or ''}:{user_name or ''}"

    def get_history(self, wallet_address: Optional[str], user_name: Optional[str]) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        key = self._get_key(wallet_address, user_name)

        if self.use_redis:
            try:
                history_str = self.redis.get(key)
                return json.loads(history_str) if history_str else []
            except Exception as e:
                print(f"Redis get error: {str(e)}. Falling back to memory store.")
                self.use_redis = False  # Disable Redis for future calls
                return self.memory_store.get(key, [])
        else:
            return self.memory_store.get(key, [])

    def add_entry(self,
                 wallet_address: Optional[str],
                 user_name: Optional[str],
                 entry_type: str,
                 command: str,
                 response: Dict[str, Any]):
        """Add a new entry to the conversation history."""
        key = self._get_key(wallet_address, user_name)
        history = self.get_history(wallet_address, user_name)

        # Add timestamp to entry
        entry = {
            'type': entry_type,
            'command': command,
            'response': response,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Add entry and keep only last 50 messages
        history.append(entry)
        if len(history) > 50:
            history = history[-50:]

        if self.use_redis:
            try:
                # Store in Redis with 24-hour expiration
                self.redis.setex(
                    key,
                    timedelta(hours=24),
                    json.dumps(history)
                )
            except Exception as e:
                print(f"Redis set error: {str(e)}. Falling back to memory store.")
                self.use_redis = False  # Disable Redis for future calls
                self.memory_store[key] = history
        else:
            self.memory_store[key] = history

    def should_respond_to_greeting(self,
                                 wallet_address: Optional[str],
                                 user_name: Optional[str],
                                 cmd_lower: str) -> bool:
        """Determine if we should respond to a greeting based on conversation history."""
        history = self.get_history(wallet_address, user_name)
        if not history:
            return True

        # Don't respond to the same greeting within 5 messages
        recent_greetings = sum(1 for msg in history[-5:] if msg.get('type') == 'greeting')
        return recent_greetings == 0

    def get_recent_context(self,
                          wallet_address: Optional[str],
                          user_name: Optional[str],
                          num_messages: int = 5) -> str:
        """Get recent conversation context for AI."""
        history = self.get_history(wallet_address, user_name)
        if not history:
            return ""

        context = "\nRecent conversation:\n"
        for entry in history[-num_messages:]:
            # Format user message
            context += f"User: {entry['command']}\n"

            # Format agent response
            if isinstance(entry['response'], dict):
                content = entry['response'].get('content', '')
                if isinstance(content, dict):
                    # Handle structured responses (like swap confirmations)
                    if content.get('type') == 'brian_confirmation':
                        context += f"Assistant: {content.get('message', '')}\n"
                    elif content.get('type') == 'swap_confirmation':
                        context += f"Assistant: {content.get('message', '')}\n"
                    else:
                        context += f"Assistant: {str(content)}\n"
                else:
                    context += f"Assistant: {content}\n"
            else:
                context += f"Assistant: {str(entry['response'])}\n"

            # Add a separator between conversations
            context += "---\n"

        return context

# Create a singleton instance
chat_history_service = ChatHistoryService()