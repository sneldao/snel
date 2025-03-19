"""
Shim implementation to replace emp-agents models.
This allows code that might still reference emp-agents to work without requiring the actual dependency.
"""
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Base classes
class AgentBase:
    """Simple replacement for emp_agents.AgentBase"""
    def __init__(self, *args, **kwargs):
        logger.info("Created shim AgentBase")

class Provider:
    """Simple replacement for emp_agents.models.Provider"""
    def __init__(self, *args, **kwargs):
        logger.info("Created shim Provider")

# Message types - all implemented without dataclass to avoid parameter ordering issues
class Message:
    """Simple replacement for emp_agents.models.Message"""
    def __init__(self, content: str, role: str = "user"):
        self.content = content
        self.role = role

class UserMessage(Message):
    """Simple replacement for emp_agents.models.UserMessage"""
    def __init__(self, content: str):
        super().__init__(content=content, role="user")

class AssistantMessage(Message):
    """Simple replacement for emp_agents.models.AssistantMessage"""
    def __init__(self, content: str, tool_calls: List[Any] = None):
        super().__init__(content=content, role="assistant")
        self.tool_calls = tool_calls or []

class ToolCall:
    """Simple replacement for emp_agents.models.ToolCall"""
    def __init__(self, name: str, arguments: Dict[str, Any]):
        self.name = name
        self.arguments = arguments

@dataclass
class ToolMessage(Message):
    """A message containing a tool call result."""
    tool_call_id: str
    content: str = ""
    role: str = "tool"
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "content": self.content,
            "role": self.role,
            "tool_call_id": self.tool_call_id,
            "name": self.name
        }

# OpenAI specific replacements
class OpenAIModelType:
    """Simple replacement for emp_agents.providers.OpenAIModelType"""
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4_VISION = "gpt-4-vision"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

# Package-level imports
from app.utils.providers import OpenAIProvider  # Import our own OpenAIProvider

# Utility functions
def count_tokens(text: str) -> int:
    """Simple replacement for emp_agents.utils.count_tokens"""
    # Simple estimate: ~4 chars per token
    return len(text) // 4 