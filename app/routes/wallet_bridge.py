from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel
import os

from app.services.wallet_bridge_service import WalletBridgeService

router = APIRouter()
wallet_bridge_service = WalletBridgeService(os.getenv("REDIS_URL"))

class TransactionRequest(BaseModel):
    user_id: str
    platform: str
    transaction_data: Dict[str, Any]
    transaction_type: Optional[str] = "transaction"

class TransactionCallback(BaseModel):
    uid: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/transaction/create")
async def create_transaction(request: TransactionRequest):
    """Create a new transaction request."""
    result = await wallet_bridge_service.create_transaction_request(
        user_id=request.user_id,
        platform=request.platform,
        transaction_data=request.transaction_data,
        transaction_type=request.transaction_type
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.get("/transaction/{tx_id}")
async def get_transaction(tx_id: str):
    """Get transaction data for the bridge page."""
    result = await wallet_bridge_service.get_transaction_status(tx_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
        
    return result["data"]["data"]  # Return just the transaction data for the bridge

@router.post("/callback/{tx_id}")
async def transaction_callback(tx_id: str, callback: TransactionCallback):
    """Handle callback from the bridge page."""
    status = "completed" if callback.success else "failed"
    result = await wallet_bridge_service.update_transaction_status(
        tx_id=tx_id,
        status=status,
        result=callback.result if callback.success else {"error": callback.error}
    )
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
        
    return result

@router.get("/bridge")
async def serve_bridge_page():
    """Serve the wallet bridge HTML page."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    return FileResponse(os.path.join(static_dir, "wallet-bridge.html")) 