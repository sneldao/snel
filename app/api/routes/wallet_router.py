from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
import logging

from app.api.dependencies import get_wallet_service, get_redis_service
from app.services.wallet_service import WalletService
from app.services.redis_service import RedisService
from app.models.wallet import (
    ChainInfo, WalletInfoResponse, WalletCreationResponse, 
    ChainSwitchResponse, Transaction, TransactionResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["wallet"])

@router.get("/chains", response_model=List[Dict[str, Any]])
async def get_supported_chains(
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get a list of supported blockchain networks."""
    return await wallet_service.get_supported_chains()

@router.post("/create", response_model=WalletCreationResponse)
async def create_wallet(
    user_id: str = Body(..., embed=True),
    platform: str = Body(..., embed=True),
    chain: Optional[str] = Body(None, embed=True),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Create a new wallet for a user."""
    try:
        result = await wallet_service.create_wallet(
            user_id=user_id,
            platform=platform,
            chain=chain or "scroll_sepolia"
        )
        return result
    except Exception as e:
        logger.exception(f"Error creating wallet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create wallet: {str(e)}"
        )

@router.get("/info/{platform}/{user_id}", response_model=WalletInfoResponse)
async def get_wallet_info(
    platform: str,
    user_id: str,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get wallet information for a user."""
    try:
        result = await wallet_service.get_wallet_info(
            user_id=user_id,
            platform=platform
        )
        return result
    except Exception as e:
        logger.exception(f"Error getting wallet info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get wallet info: {str(e)}"
        )

@router.post("/switch-chain", response_model=ChainSwitchResponse)
async def switch_chain(
    user_id: str = Body(..., embed=True),
    platform: str = Body(..., embed=True),
    chain: str = Body(..., embed=True),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Switch the blockchain network for a user's wallet."""
    try:
        result = await wallet_service.switch_chain(
            user_id=user_id,
            platform=platform,
            chain=chain
        )
        return result
    except Exception as e:
        logger.exception(f"Error switching chain: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch chain: {str(e)}"
        ) 