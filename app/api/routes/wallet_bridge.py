from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import logging
from fastapi.responses import JSONResponse

from app.services.wallet_bridge_service import WalletBridgeService
from app.services.redis_service import RedisService
from app.dependencies import get_redis_service, get_wallet_bridge_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/wallet-bridge",
    tags=["wallet-bridge"],
)


class WalletConnectionRequest(BaseModel):
    wallet_address: str
    connection_id: str


class ConnectionStatusResponse(BaseModel):
    success: bool
    status: str
    connection_id: str
    user_id: Optional[str] = None
    platform: Optional[str] = None
    wallet_address: Optional[str] = None
    error: Optional[str] = None


@router.post("/connect", response_model=Dict[str, Any])
async def connect_wallet(
    request: WalletConnectionRequest,
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service),
):
    """
    Complete a wallet connection after user has connected their wallet through the bridge page.
    """
    try:
        logger.info(f"Processing wallet connection for ID: {request.connection_id}")
        
        result = await wallet_bridge_service.complete_wallet_connection(
            request.connection_id, 
            request.wallet_address
        )
        
        if not result.get("success", False):
            logger.error(f"Failed to complete wallet connection: {result.get('error')}")
            return JSONResponse(
                status_code=400, 
                content={"success": False, "error": result.get("error", "Unknown error")}
            )
            
        return result
        
    except Exception as e:
        logger.exception(f"Error connecting wallet: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/status/{connection_id}", response_model=ConnectionStatusResponse)
async def check_connection_status(
    connection_id: str,
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service),
):
    """
    Check the status of a wallet connection.
    """
    try:
        logger.info(f"Checking connection status for ID: {connection_id}")
        
        result = await wallet_bridge_service.get_connection_status(connection_id)
        
        if not result.get("success", False):
            return ConnectionStatusResponse(
                success=False,
                status=result.get("status", "error"),
                connection_id=connection_id,
                error=result.get("error", "Unknown error")
            )
            
        return ConnectionStatusResponse(
            success=True,
            status=result.get("status", "unknown"),
            connection_id=connection_id,
            user_id=result.get("user_id"),
            platform=result.get("platform"),
            wallet_address=result.get("wallet_address")
        )
        
    except Exception as e:
        logger.exception(f"Error checking connection status: {e}")
        return ConnectionStatusResponse(
            success=False,
            status="error",
            connection_id=connection_id,
            error=str(e)
        )


@router.get("/create", response_model=Dict[str, Any])
async def create_connection(
    user_id: str = Query(..., description="User ID (e.g. Telegram ID)"),
    platform: str = Query("telegram", description="Platform (telegram, web, etc.)"),
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service),
):
    """
    Create a new wallet connection request.
    """
    try:
        logger.info(f"Creating connection for {platform}:{user_id}")
        
        connection_id = str(uuid.uuid4())
        
        result = await wallet_bridge_service.register_pending_connection(
            connection_id=connection_id,
            user_id=user_id,
            platform=platform
        )
        
        if not result.get("success", False):
            logger.error(f"Failed to create connection: {result.get('error')}")
            return JSONResponse(
                status_code=400, 
                content={"success": False, "error": result.get("error", "Unknown error")}
            )
            
        return result
        
    except Exception as e:
        logger.exception(f"Error creating connection: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        ) 