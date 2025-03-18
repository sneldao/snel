"""
Custom provider implementations to replace external dependencies.
"""
import os
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider:
    """Simple replacement for emp_agents.providers.OpenAIProvider"""
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        logger.info("Created custom OpenAIProvider")
        
    def __repr__(self):
        return f"OpenAIProvider(api_key=***)" 