from fastapi import Depends, HTTPException, Header
from typing import Optional
import os

from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.redis_service import RedisService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.base import PointlessAgent

# Don't import AgentFactory here to avoid circular imports

async def get_token_service() -> TokenService:
    """Get an instance of TokenService."""
    return TokenService()

async def get_openai_key(x_openai_key: Optional[str] = Header(None)) -> str:
    """Get OpenAI API key from headers or environment."""
    api_key = x_openai_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API Key is required (either in header or environment)"
        )
    return api_key

async def get_swap_agent(openai_api_key: str = Depends(get_openai_key)) -> SimpleSwapAgent:
    """Get an instance of SwapAgent."""
    return SimpleSwapAgent()

async def get_price_agent(openai_api_key: str = Depends(get_openai_key)) -> PriceAgent:
    """Get an instance of PriceAgent."""
    return PriceAgent(provider="openai")

async def get_base_agent(openai_api_key: str = Depends(get_openai_key)) -> PointlessAgent:
    """Get an instance of BaseAgent."""
    return PointlessAgent(prompt="", model="gpt-4-turbo-preview")

async def get_swap_service(
    token_service: TokenService = Depends(get_token_service),
    swap_agent: SimpleSwapAgent = Depends(get_swap_agent)
) -> SwapService:
    """Get an instance of SwapService."""
    return SwapService(token_service=token_service, swap_agent=swap_agent)

async def get_redis_service() -> RedisService:
    """Get an instance of RedisService."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return RedisService(redis_url=redis_url) 