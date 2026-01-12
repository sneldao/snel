"""
MNEE Protocol API Endpoints

Handles MNEE specific operations, including the Relayer flow for Ethereum.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from decimal import Decimal

from app.protocols.mnee_adapter import MNEEAdapter
from app.protocols.registry import protocol_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mnee", tags=["mnee"])

def get_mnee_adapter() -> MNEEAdapter:
    """Dependency to get MNEE adapter instance."""
    # We can get it from registry or instantiate directly. 
    # Since it has state (Web3 connection), registry is better if initialized there.
    # But MNEEAdapter is lightweight enough to instantiate if needed, 
    # though reusing the Web3 connection is preferred.
    
    # Check registry first
    adapter = protocol_registry.get_protocol("mnee")
    if adapter and isinstance(adapter, MNEEAdapter):
        return adapter
    
    # Fallback
    return MNEEAdapter()

class RelayedPaymentRequest(BaseModel):
    """Request to execute a relayed payment on Ethereum."""
    user_address: str = Field(..., description="User wallet address (sender)")
    recipient_address: str = Field(..., description="Recipient wallet address")
    amount: float = Field(..., gt=0, description="Amount in MNEE")

class RelayedPaymentResponse(BaseModel):
    """Response for relayed payment execution."""
    success: bool
    tx_hash: str
    amount_atomic: int

class AllowanceResponse(BaseModel):
    """Response for allowance check."""
    allowance: str # String to handle large integers
    allowance_atomic: int
    relayer_address: str
    is_sufficient: bool

@router.get("/relayer-address")
async def get_relayer_address(
    adapter: MNEEAdapter = Depends(get_mnee_adapter)
):
    """Get the configured Relayer address."""
    address = adapter.get_relayer_address()
    if not address:
        raise HTTPException(status_code=503, detail="Relayer not configured")
    return {"address": address}

@router.get("/allowance/{wallet_address}")
async def check_allowance(
    wallet_address: str,
    amount_needed: Optional[float] = None,
    adapter: MNEEAdapter = Depends(get_mnee_adapter)
):
    """
    Check if the user has approved the Relayer to spend MNEE.
    """
    relayer_address = adapter.get_relayer_address()
    if not relayer_address:
        raise HTTPException(status_code=503, detail="Relayer not configured")
    
    try:
        allowance_atomic = await adapter.check_allowance(wallet_address, relayer_address)
        allowance_decimal = adapter.from_atomic_amount(allowance_atomic)
        
        is_sufficient = True
        if amount_needed:
            amount_needed_atomic = adapter.to_atomic_amount(Decimal(str(amount_needed)))
            is_sufficient = allowance_atomic >= amount_needed_atomic
            
        return AllowanceResponse(
            allowance=str(allowance_decimal),
            allowance_atomic=allowance_atomic,
            relayer_address=relayer_address,
            is_sufficient=is_sufficient
        )
        
    except Exception as e:
        logger.error(f"Allowance check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-relayed-payment", response_model=RelayedPaymentResponse)
async def execute_relayed_payment(
    request: RelayedPaymentRequest,
    adapter: MNEEAdapter = Depends(get_mnee_adapter)
):
    """
    Execute a payment using the Relayer (transferFrom).
    User must have approved the Relayer beforehand.
    """
    try:
        # 1. Convert amount
        amount_atomic = adapter.to_atomic_amount(Decimal(str(request.amount)))
        
        # 2. Check allowance again (safety check)
        relayer_address = adapter.get_relayer_address()
        allowance = await adapter.check_allowance(request.user_address, relayer_address)
        
        if allowance < amount_atomic:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient allowance. Approved: {allowance}, Needed: {amount_atomic}"
            )
            
        # 3. Execute
        tx_hash = await adapter.execute_relayed_transfer(
            user_address=request.user_address,
            recipient_address=request.recipient_address,
            amount_atomic=amount_atomic
        )
        
        return RelayedPaymentResponse(
            success=True,
            tx_hash=tx_hash,
            amount_atomic=amount_atomic
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Relayed payment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
