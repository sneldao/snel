from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

from app.api.dependencies import get_redis_service
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["wallet"])

class WalletData(BaseModel):
    """Wallet data model."""
    address: str
    privateKey: str
    chainId: int
    created_at: Optional[str] = None

class WalletLinkRequest(BaseModel):
    """Request to link a wallet to a messaging platform user."""
    platform: str
    user_id: str
    wallet_address: str
    wallet_data: Optional[Dict[str, Any]] = None

class TokenBalance(BaseModel):
    """Token balance model."""
    token: str
    symbol: str
    balance: str
    decimals: int
    price_usd: Optional[float] = None
    value_usd: Optional[float] = None

class WalletBalances(BaseModel):
    """Wallet balances response."""
    address: str
    chain_id: int
    eth_balance: str
    tokens: List[TokenBalance]

@router.post("/link-wallet", response_model=Dict[str, Any])
async def link_wallet(
    request: WalletLinkRequest,
    redis_service: RedisService = Depends(get_redis_service)
):
    """Link a wallet to a messaging platform user."""
    try:
        # Store the wallet address for the user
        user_key = f"messaging:{request.platform}:user:{request.user_id}:wallet"
        await redis_service.set(user_key, request.wallet_address)
        
        # Store the reverse mapping
        reverse_key = f"wallet:{request.wallet_address}:{request.platform}:user"
        await redis_service.set(reverse_key, request.user_id)
        
        # If wallet data is provided, store it
        if request.wallet_data:
            wallet_key = f"wallet:{request.wallet_address}:data"
            await redis_service.set(wallet_key, request.wallet_data)
        
        return {
            "success": True,
            "message": f"Wallet {request.wallet_address[:6]}...{request.wallet_address[-4:]} linked successfully to {request.platform} user {request.user_id}"
        }
        
    except Exception as e:
        logger.exception(f"Error linking wallet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to link wallet: {str(e)}"
        )

@router.get("/{wallet_address}", response_model=Dict[str, Any])
async def get_wallet_data(
    wallet_address: str,
    redis_service: RedisService = Depends(get_redis_service)
):
    """Get wallet data."""
    try:
        wallet_key = f"wallet:{wallet_address}:data"
        wallet_data = await redis_service.get(wallet_key)
        
        if not wallet_data:
            raise HTTPException(
                status_code=404,
                detail=f"Wallet data not found for {wallet_address}"
            )
        
        return wallet_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting wallet data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get wallet data: {str(e)}"
        )

@router.get("/{wallet_address}/balances", response_model=Dict[str, Any])
async def get_wallet_balances(
    wallet_address: str,
    chain_id: int = 534351,  # Default to Scroll Sepolia
    redis_service: RedisService = Depends(get_redis_service)
):
    """Get wallet balances."""
    try:
        # For now, return mock data for Scroll Sepolia
        # In a real implementation, this would query the blockchain
        
        # Check if we have cached balance data
        balance_key = f"wallet:{wallet_address}:chain:{chain_id}:balances"
        cached_balances = await redis_service.get(balance_key)
        
        if cached_balances:
            return cached_balances
        
        # Mock data for testing
        mock_balances = {
            "address": wallet_address,
            "chain_id": chain_id,
            "eth_balance": "0.1",
            "tokens": [
                {
                    "token": "0x5300000000000000000000000000000000000004",
                    "symbol": "USDC",
                    "balance": "100.0",
                    "decimals": 6,
                    "price_usd": 1.0,
                    "value_usd": 100.0
                },
                {
                    "token": "0x5300000000000000000000000000000000000002",
                    "symbol": "WETH",
                    "balance": "0.05",
                    "decimals": 18,
                    "price_usd": 3000.0,
                    "value_usd": 150.0
                }
            ]
        }
        
        # Cache the balances for 5 minutes
        await redis_service.set(balance_key, mock_balances, expire=300)
        
        return mock_balances
        
    except Exception as e:
        logger.exception(f"Error getting wallet balances: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get wallet balances: {str(e)}"
        )

@router.delete("/{wallet_address}", response_model=Dict[str, Any])
async def delete_wallet_data(
    wallet_address: str,
    redis_service: RedisService = Depends(get_redis_service)
):
    """Delete wallet data."""
    try:
        wallet_key = f"wallet:{wallet_address}:data"
        wallet_data = await redis_service.get(wallet_key)
        
        if not wallet_data:
            return {
                "success": True,
                "message": f"No wallet data found for {wallet_address}"
            }
        
        # Delete the wallet data
        await redis_service.delete(wallet_key)
        
        # Find and delete any user mappings
        platform_keys = await redis_service.keys(f"wallet:{wallet_address}:*:user")
        for key in platform_keys:
            parts = key.split(":")
            if len(parts) >= 4:
                platform = parts[2]
                user_id = await redis_service.get(key)
                if user_id:
                    user_key = f"messaging:{platform}:user:{user_id}:wallet"
                    await redis_service.delete(user_key)
                await redis_service.delete(key)
        
        return {
            "success": True,
            "message": f"Wallet data for {wallet_address[:6]}...{wallet_address[-4:]} deleted successfully"
        }
        
    except Exception as e:
        logger.exception(f"Error deleting wallet data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete wallet data: {str(e)}"
        ) 