import os
import logging
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from emp_agents.providers import OpenAIProvider, OpenAIModelType
from app.services.redis_service import RedisService
from app.services.command_store import CommandStore
from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.agents.swap_agent import SwapAgent

logger = logging.getLogger(__name__)

# OpenAI API key header
openai_key_header = APIKeyHeader(name="X-OpenAI-Key", auto_error=False)

def get_openai_key(api_key: str = Depends(openai_key_header)) -> str:
    """Get the OpenAI API key from header or environment."""
    # Check if we're in development mode
    is_development = os.environ.get("ENVIRONMENT") == "development"
    
    # First try to get from header (user-provided key)
    if api_key:
        logger.info("Using user-provided OpenAI API key")
        return api_key

    # Then try environment variable (only in development)
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key and is_development:
        logger.info("Using development OpenAI API key from environment")
        return env_key
    
    # In production, require user-provided key
    if not is_development:
        logger.error("No OpenAI API key provided in production")
        raise HTTPException(
            status_code=401,
            detail="OpenAI API Key is required in the X-OpenAI-Key header for production use"
        )
    
    # If we're in development but no key is available
    logger.error("No OpenAI API key available")
    raise HTTPException(
        status_code=401,
        detail="OpenAI API Key is required (either in header or environment)"
    )

def get_openai_provider(openai_key: str = Depends(get_openai_key)) -> OpenAIProvider:
    """Get an OpenAI provider instance."""
    return OpenAIProvider(
        api_key=openai_key,
        default_model=OpenAIModelType.gpt4o
    )

def get_redis_service() -> RedisService:
    """Get a Redis service instance."""
    return RedisService()

def get_command_store(redis_service: RedisService = Depends(get_redis_service)) -> CommandStore:
    """Get a command store instance."""
    return CommandStore(redis_service)

def get_token_service() -> TokenService:
    """Get a token service instance."""
    return TokenService()

def get_swap_agent(openai_key: str = Depends(get_openai_key)) -> SwapAgent:
    """Get a swap agent instance."""
    provider = OpenAIProvider(api_key=openai_key)
    return SwapAgent(provider=provider)

def get_swap_service(
    token_service: TokenService = Depends(get_token_service),
    swap_agent: SwapAgent = Depends(get_swap_agent)
) -> SwapService:
    """Get a swap service instance."""
    return SwapService(token_service=token_service, swap_agent=swap_agent)

# For backward compatibility, we'll keep a simplified version of get_pipeline
# that returns our swap service instead
def get_pipeline(openai_key: str = Depends(get_openai_key), request: Request = None):
    """
    Legacy function to maintain backward compatibility.
    
    This now returns a simple object with a process method that delegates to the swap service.
    """
    logger.warning("get_pipeline is deprecated, use get_swap_service instead")
    
    # Create services
    provider = OpenAIProvider(api_key=openai_key)
    swap_agent = SwapAgent(provider=provider)
    token_service = TokenService()
    swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
    
    # Create a simple object that mimics the pipeline interface
    class LegacyPipeline:
        async def process(self, tweet):
            """Process a tweet using the swap agent."""
            # Extract the command from the tweet
            command = tweet.text if hasattr(tweet, 'text') else str(tweet)
            
            # Use the swap agent to process the command
            result = await swap_agent.process_swap(command)
            
            # Return the result
            return result
    
    return LegacyPipeline() 