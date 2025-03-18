from fastapi import Depends, HTTPException, Header
from typing import Optional
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
from app.agents.telegram_agent import TelegramAgent

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local", override=True)  # Override with .env.local if it exists

# Conditionally import SmartWalletService if available
try:
    from app.services.smart_wallet_service import SmartWalletService
    SMART_WALLET_AVAILABLE = True
except ImportError:
    SMART_WALLET_AVAILABLE = False
    SmartWalletService = None

# Check if CDP SDK is enabled
USE_CDP_SDK = os.getenv("USE_CDP_SDK", "false").lower() in ["true", "1", "yes"]

# Singleton instance of RedisService
_redis_service: Optional[RedisService] = None

# Singleton instance of TokenService
_token_service: Optional[TokenService] = None

# Singleton instance of WalletService
_wallet_service: Optional[WalletService] = None

# Singleton instance of GeminiService
_gemini_service: Optional[GeminiService] = None

# Singleton instance of TelegramAgent
_telegram_agent: Optional[TelegramAgent] = None

logger = logging.getLogger(__name__)

async def get_redis_service() -> Optional[RedisService]:
    """Get a Redis service instance if configured."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    return RedisService(redis_url=redis_url)

async def get_token_service() -> TokenService:
    """Get or create token service instance."""
    global _token_service
    
    if _token_service is None:
        _token_service = TokenService()
        
    return _token_service

async def get_wallet_service(redis_service: Optional[RedisService] = Depends(get_redis_service)) -> WalletService:
    """Get a wallet service instance."""
    redis_url = os.getenv("REDIS_URL")
    return WalletService(redis_service=redis_service)

async def get_smart_wallet_service() -> Optional[SmartWalletService]:
    """Get a smart wallet service instance if available."""
    if not SMART_WALLET_AVAILABLE:
        logger.warning("SmartWalletService not available - CDP features will be limited")
        return None
        
    if not USE_CDP_SDK:
        logger.info("USE_CDP_SDK is disabled - CDP features will be limited")
        return None
    
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.warning("Redis URL not set - SmartWalletService requires Redis")
            return None
            
        # Check for CDP API keys
        cdp_api_key_name = os.getenv("CDP_API_KEY_NAME")
        cdp_api_key_private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY")
        
        if not cdp_api_key_name or not cdp_api_key_private_key:
            logger.warning("CDP API keys not configured properly - Check CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY")
            return None
            
        # Initialize SmartWalletService
        service = SmartWalletService(redis_url=redis_url)
        logger.info("SmartWalletService initialized successfully")
        return service
    except Exception as e:
        logger.error(f"Error initializing SmartWalletService: {e}")
        # Log more details about the error
        import traceback
        logger.error(f"Error details: {traceback.format_exc()}")
        return None

# Factory function to get the appropriate wallet service
async def get_wallet_service_factory(
    wallet_service: WalletService = Depends(get_wallet_service),
    smart_wallet_service: Optional[SmartWalletService] = Depends(get_smart_wallet_service)
) -> WalletService:
    """
    Get the appropriate wallet service based on configuration.
    
    If USE_CDP_SDK is enabled and SmartWalletService is available, return that.
    Otherwise, fall back to the standard WalletService.
    """
    if USE_CDP_SDK and smart_wallet_service is not None:
        logger.info("Using SmartWalletService with Coinbase CDP")
        return smart_wallet_service
    
    if USE_CDP_SDK:
        logger.warning("USE_CDP_SDK is enabled but SmartWalletService is not available - using basic WalletService")
    else:
        logger.info("Using basic WalletService (USE_CDP_SDK is disabled)")
        
    return wallet_service

async def get_gemini_service() -> GeminiService:
    """
    Get a GeminiService instance.
    
    Uses a singleton pattern to return the same instance on subsequent calls.
    
    Returns:
        GeminiService instance
    """
    global _gemini_service
    if _gemini_service is None:
        # Get the Gemini API key from environment
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY not set, AI responses will be limited")
            
        _gemini_service = GeminiService(api_key=gemini_api_key)
        
        # Try to check model availability - don't await to avoid blocking
        try:
            logger.info("GeminiService initialized")
        except Exception as e:
            logger.warning(f"Error in Gemini service initialization: {e}")
        
    return _gemini_service

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

async def get_telegram_agent(
    token_service: TokenService = Depends(get_token_service),
    swap_service: SwapService = Depends(get_swap_service),
    wallet_service: WalletService = Depends(get_wallet_service_factory),
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> TelegramAgent:
    """
    Get a TelegramAgent instance with the necessary dependencies.
    
    Args:
        token_service: Service for token operations
        swap_service: Service for swap operations
        wallet_service: Service for wallet operations (SmartWalletService if available)
        gemini_service: Service for AI-powered responses
        
    Returns:
        TelegramAgent instance
    """
    # Return a singleton instance of the agent with dependencies
    global _telegram_agent
    if _telegram_agent is None:
        _telegram_agent = TelegramAgent(
            token_service=token_service,
            swap_service=swap_service,
            wallet_service=wallet_service,
            gemini_service=gemini_service
        )
        
    return _telegram_agent 