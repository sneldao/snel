from fastapi import Depends, HTTPException, Header
from typing import Optional
import os
import logging

from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.redis_service import RedisService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.base import PointlessAgent
from app.services.wallet_service import WalletService

# Don't import AgentFactory here to avoid circular imports

# Singleton instance of RedisService
_redis_service: Optional[RedisService] = None

# Singleton instance of TokenService
_token_service: Optional[TokenService] = None

# Singleton instance of WalletService
_wallet_service: Optional[WalletService] = None

logger = logging.getLogger(__name__)

async def get_redis_service() -> RedisService:
    """Get or create Redis service instance."""
    global _redis_service
    
    if _redis_service is None:
        try:
            # Get Redis URL from environment or use default
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            _redis_service = RedisService(redis_url=redis_url)
            await _redis_service.connect()
        except Exception as e:
            logger.warning(f"Failed to initialize Redis service: {e}. Some features may be limited.")
            # Create a dummy Redis service to prevent errors
            _redis_service = RedisService(redis_url="redis://localhost:6379/0")
    
    return _redis_service

async def get_token_service() -> TokenService:
    """Get or create token service instance."""
    global _token_service
    
    if _token_service is None:
        _token_service = TokenService()
        
    return _token_service

async def get_wallet_service(
    redis_service: RedisService = Depends(get_redis_service)
) -> WalletService:
    """Get or create wallet service instance."""
    global _wallet_service
    
    if _wallet_service is None:
        _wallet_service = WalletService(redis_service=redis_service)
        
    return _wallet_service

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