"""
API routes for token bridging operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.models.commands import (
    BridgeRequest,
    BridgeQuoteResponse,
    BridgeExecuteResponse,
    TransactionStatus
)
from app.services.brian.client import brian_client

router = APIRouter(prefix="/bridges", tags=["bridges"])

@router.post("/quote", response_model=BridgeQuoteResponse)
async def get_bridge_quote(request: BridgeRequest) -> Dict[str, Any]:
    """
    Get a quote for bridging tokens across chains.
    """
    try:
        quote = await brian_client.get_quote(
            from_token=request.from_token,
            to_token=request.to_token,
            amount=request.amount,
            from_chain_id=request.from_chain_id,
            to_chain_id=request.to_chain_id
        )
        return BridgeQuoteResponse(**quote)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/execute", response_model=BridgeExecuteResponse)
async def execute_bridge(quote_id: str, wallet_address: str) -> Dict[str, Any]:
    """
    Execute a bridge transaction using a quote ID.
    """
    try:
        result = await brian_client.execute_bridge(
            quote_id=quote_id,
            wallet_address=wallet_address
        )
        return BridgeExecuteResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status/{tx_hash}", response_model=TransactionStatus)
async def get_bridge_status(tx_hash: str, chain_id: int) -> Dict[str, Any]:
    """
    Get the status of a bridge transaction.
    """
    try:
        status = await brian_client.get_transaction_status(
            tx_hash=tx_hash,
            chain_id=chain_id
        )
        return TransactionStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
