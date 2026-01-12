"""
Unified Payment API - Protocol-Agnostic Payment Execution

This endpoint intelligently routes payments to x402 (Cronos) or MNEE (Ethereum)
based on the network and token context.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal

from app.services.payment_router import payment_router, PaymentPreparationResult

router = APIRouter(prefix="/payment", tags=["payment"])

class UnifiedPrepareRequest(BaseModel):
    """Request to prepare a payment regardless of protocol."""
    network: str = Field(..., description="cronos-mainnet, ethereum-mainnet, etc.")
    token_symbol: str = Field("USDC", description="USDC or MNEE")
    user_address: str
    recipient_address: str
    amount: float

class UnifiedSubmitRequest(BaseModel):
    """Request to submit a prepared payment."""
    protocol: Literal["x402", "mnee"]
    data: Dict[str, Any] = Field(..., description="Protocol-specific submission data")

@router.post("/execute/prepare", response_model=PaymentPreparationResult)
async def prepare_payment(request: UnifiedPrepareRequest):
    """
    Step 1: Get the required action (Sign Typed Data OR Approve Allowance).
    """
    try:
        return await payment_router.prepare_payment(
            network=request.network,
            user_address=request.user_address,
            recipient_address=request.recipient_address,
            amount=request.amount,
            token_symbol=request.token_symbol
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute/submit")
async def submit_payment(request: UnifiedSubmitRequest):
    """
    Step 2: Execute the payment using the signed data or approved allowance.
    """
    try:
        return await payment_router.submit_payment(
            protocol=request.protocol,
            submission_data=request.data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))