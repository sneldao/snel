from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
import uuid

from app.api.dependencies import get_wallet_service, get_redis_service, get_wallet_bridge_service
from app.services.wallet_service import WalletService
from app.services.redis_service import RedisService
from app.services.wallet_bridge_service import WalletBridgeService
from app.models.wallet import (
    ChainInfo, WalletInfoResponse, WalletCreationResponse, 
    ChainSwitchResponse, Transaction, TransactionResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"],
    responses={404: {"description": "Not found"}},
)

@router.get("/chains", response_model=List[Dict[str, Any]])
async def get_supported_chains(
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get a list of supported blockchain networks."""
    return await wallet_service.get_supported_chains()

@router.post("/create", response_model=WalletCreationResponse)
async def create_wallet(
    user_id: str = Body(...),
    platform: str = Body(...),
    chain: Optional[str] = Body(None),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Create a new wallet for a user."""
    try:
        result = await wallet_service.create_wallet(user_id, platform, chain)
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
    user_id: str = Body(...),
    platform: str = Body(...),
    chain: str = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Switch chain for a specific wallet."""
    try:
        result = await wallet_service.switch_chain(user_id, platform, chain)
        return result
    except Exception as e:
        logger.exception(f"Error switching chain: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to switch chain: {str(e)}"
        )

@router.get("/connect/{user_id}/{platform}")
async def connect_wallet(
    user_id: str, 
    platform: str = "telegram",
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service)
) -> JSONResponse:
    """Generate a wallet connect URL for a specific user.
    
    Args:
        user_id: The user ID to connect wallet for
        platform: The platform (telegram, discord, etc.)
        
    Returns:
        JSON with connect URL and status
    """
    try:
        logger.info(f"Creating wallet connect URL for {platform}:{user_id}")
        
        # Generate a unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Register this pending connection in the service
        register_result = await wallet_bridge_service.register_pending_connection(
            connection_id=connection_id,
            user_id=user_id,
            platform=platform
        )
        
        if not register_result.get("success", False):
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": register_result.get("error", "Failed to register connection")}
            )
            
        # Generate the bridge URL
        connect_url = wallet_bridge_service.generate_connect_url(connection_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "connection_id": connection_id,
                "connect_url": connect_url,
                "expires_in": 300  # 5 minutes
            }
        )
        
    except Exception as e:
        logger.exception(f"Error creating wallet connect URL: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/connect/verify")
async def verify_wallet_connection(
    connection_data: Dict[str, Any] = Body(...),
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service)
) -> JSONResponse:
    """Verify a wallet connection signature.
    
    Args:
        connection_data: Contains connection_id, wallet_address, signature, and message
        
    Returns:
        JSON with verification status
    """
    try:
        connection_id = connection_data.get("connection_id")
        wallet_address = connection_data.get("wallet_address")
        signature = connection_data.get("signature")
        message = connection_data.get("message")
        
        if not all([connection_id, wallet_address, signature, message]):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Missing required fields"}
            )
            
        logger.info(f"Verifying wallet connection for ID {connection_id} and address {wallet_address}")
        
        # Verify the connection
        result = await wallet_bridge_service.verify_wallet_connection(
            connection_id=connection_id,
            wallet_address=wallet_address,
            signature=signature,
            message=message
        )
        
        if result.get("success", False):
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Wallet connected successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get("error", "Connection verification failed")
                }
            )
            
    except Exception as e:
        logger.exception(f"Error verifying wallet connection: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/wallet-bridge/status/{connection_id}")
async def wallet_bridge_status(
    connection_id: str,
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service)
) -> JSONResponse:
    """Get the status of a wallet connection.
    
    Args:
        connection_id: The unique connection ID
        
    Returns:
        JSON with connection status
    """
    try:
        logger.info(f"Checking status of wallet connection {connection_id}")
        
        # Get connection status from service
        result = await wallet_bridge_service.get_connection_status(connection_id)
        
        return JSONResponse(
            status_code=200,
            content=result
        )
    except Exception as e:
        logger.exception(f"Error getting wallet connection status: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/wallet-bridge/connect")
async def wallet_bridge_connect(
    connection_data: Dict[str, Any] = Body(...),
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service)
) -> JSONResponse:
    """Connect a wallet through the bridge.
    
    Args:
        connection_data: Contains connection_id, wallet_address, signature
        
    Returns:
        JSON with connection status
    """
    try:
        connection_id = connection_data.get("connection_id") or connection_data.get("uid")
        wallet_address = connection_data.get("wallet_address") or connection_data.get("address")
        signature = connection_data.get("signature")
        message = connection_data.get("message", "")
        
        if not all([connection_id, wallet_address]):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Missing required fields"}
            )
        
        logger.info(f"Processing wallet connection for ID {connection_id} and address {wallet_address}")
        
        # Complete the connection
        result = await wallet_bridge_service.verify_wallet_connection(
            connection_id=connection_id,
            wallet_address=wallet_address,
            signature=signature or "placeholder",
            message=message
        )
        
        if result.get("success", False):
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Wallet connected successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get("error", "Connection verification failed")
                }
            )
    except Exception as e:
        logger.exception(f"Error completing wallet connection: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        ) 