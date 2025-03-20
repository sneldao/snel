from fastapi import Depends, HTTPException, Header
from typing import Optional, Any, TYPE_CHECKING
import os
import logging
from dotenv import load_dotenv

from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.redis_service import RedisService
from app.services.wallet_service import WalletService
from app.services.gemini_service import GeminiService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.base import PointlessAgent
from app.services.wallet_bridge_service import WalletBridgeService

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local", override=True)  # Override with .env.local if it exists

# Singleton instances
_redis_service: Optional[RedisService] = None
_token_service: Optional[TokenService] = None
_wallet_service: Optional[WalletService] = None
_gemini_service: Optional[GeminiService] = None
_wallet_bridge_service: Optional[WalletBridgeService] = None
_telegram_agent: Optional[Any] = None

logger = logging.getLogger(__name__)

async def get_openai_key(x_openai_key: Optional[str] = Header(None)) -> str:
    """Get OpenAI API key from headers or environment."""
    api_key = x_openai_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API Key is required (either in header or environment)"
        )
    return api_key

async def get_alchemy_key(x_alchemy_key: Optional[str] = Header(None)) -> str:
    """Get Alchemy API key from headers or environment."""
    api_key = x_alchemy_key or os.environ.get("ALCHEMY_KEY")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Alchemy API Key is required (either in header or environment)"
        )
    return api_key

async def get_redis_service() -> Optional[RedisService]:
    """Get a Redis service instance if configured."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    return RedisService(redis_url=redis_url)

async def get_token_service(alchemy_key: str = Depends(get_alchemy_key)) -> TokenService:
    """Get or create token service instance with Alchemy key."""
    global _token_service
    
    if _token_service is None:
        _token_service = TokenService(alchemy_key=alchemy_key)
        
    return _token_service

async def get_wallet_service(redis_service: Optional[RedisService] = Depends(get_redis_service)) -> WalletService:
    """Get a wallet service instance."""
    redis_url = os.getenv("REDIS_URL")
    return WalletService(redis_service=redis_service)

async def get_wallet_bridge_service() -> WalletBridgeService:
    """Get a WalletBridgeService instance for external wallet connections."""
    global _wallet_bridge_service
    
    if _wallet_bridge_service is None:
        redis_service = await get_redis_service()
        redis_url = redis_service.redis_url if redis_service else None
        
        _wallet_bridge_service = WalletBridgeService(redis_url=redis_url)
        logger.info("WalletBridgeService initialized")
    
    return _wallet_bridge_service

async def get_wallet_service_factory(
    wallet_service: WalletService = Depends(get_wallet_service)
) -> WalletService:
    """Get the wallet service."""
    logger.info("Using basic WalletService")
    return wallet_service

async def get_gemini_service() -> GeminiService:
    """Get a GeminiService instance."""
    global _gemini_service
    if _gemini_service is None:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not set, AI responses will be limited")
            
        _gemini_service = GeminiService(api_key=gemini_api_key)
        
        try:
            logger.info("GeminiService initialized")
        except Exception as e:
            logger.warning(f"Error in Gemini service initialization: {e}")
        
    return _gemini_service

async def get_swap_agent(openai_api_key: str = Depends(get_openai_key)) -> SimpleSwapAgent:
    """Get an instance of SwapAgent."""
    return SimpleSwapAgent(api_key=openai_api_key)

async def get_price_agent(openai_api_key: str = Depends(get_openai_key)) -> PriceAgent:
    """Get an instance of PriceAgent."""
    return PriceAgent(provider="openai", api_key=openai_api_key)

async def get_base_agent(openai_api_key: str = Depends(get_openai_key)) -> PointlessAgent:
    """Get an instance of BaseAgent."""
    return PointlessAgent(prompt="", model="gpt-4-turbo-preview", api_key=openai_api_key)

async def get_swap_service(
    token_service: TokenService = Depends(get_token_service),
    swap_agent: SimpleSwapAgent = Depends(get_swap_agent)
) -> SwapService:
    """Get an instance of SwapService."""
    return SwapService(token_service=token_service, swap_agent=swap_agent)

async def get_telegram_agent(
    token_service: TokenService = Depends(get_token_service),
    swap_service: SwapService = Depends(get_swap_service),
    wallet_service: WalletService = Depends(get_wallet_service_factory),
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service),
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> Any:
    """
    Get a TelegramAgent instance with the necessary dependencies.
    
    Args:
        token_service: Service for token operations
        swap_service: Service for swap operations
        wallet_service: Service for wallet operations
        wallet_bridge_service: Wallet bridge service for external wallet connections
        gemini_service: Service for AI-powered responses
        
    Returns:
        TelegramAgent instance
    """
    # Return a singleton instance of the agent with dependencies
    global _telegram_agent
    if _telegram_agent is None:
        from app.agents.telegram_agent import TelegramAgent
        _telegram_agent = TelegramAgent(
            token_service=token_service,
            swap_service=swap_service,
            wallet_service=wallet_service,
            wallet_bridge_service=wallet_bridge_service,
            gemini_service=gemini_service
        )
        
    return _telegram_agent 