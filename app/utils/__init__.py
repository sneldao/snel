"""
Utility modules and functions for the app.
"""

# Import and re-export our emp_agents shim
from app.utils.emp_agents import (
    AgentBase,
    Provider,
    Message,
    UserMessage,
    AssistantMessage,
    ToolCall,
    ToolMessage,
    OpenAIModelType,
    OpenAIProvider,
    count_tokens
)

# This allows imports like:
# from app.utils import AgentBase  # Instead of from app.utils import AgentBase  # Updated from emp_agents
