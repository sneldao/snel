"""Payment API endpoints for handling signed transactions."""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from app.domains.payment_actions.service import get_payment_action_service, PaymentActionService
from app.domains.payment_actions.executor import get_payment_executor, PaymentExecutor, ExecutionStatus
from app.protocols.mnee_adapter import MNEEAdapter

router = APIRouter(tags=["payments"])
logger = logging.getLogger(__name__)

class SubmitSignatureRequest(BaseModel):
    action_id: str
    signed_raw_tx: str
    wallet_address: str

class PaymentStatusResponse(BaseModel):
    action_id: str
    status: str
    ticket_id: Optional[str] = None
    transaction_hash: Optional[str] = None
    error: Optional[str] = None

@router.post("/payments/submit-signature", response_model=PaymentStatusResponse)
async def submit_signature(
    request: SubmitSignatureRequest,
    service: PaymentActionService = Depends(get_payment_action_service),
    executor: PaymentExecutor = Depends(get_payment_executor)
):
    """
    Submit a signed transaction for a pending payment action.
    """
    try:
        logger.info(f"Received signature for action {request.action_id} from {request.wallet_address}")
        
        # 1. Retrieve the action
        action = await service.get_action(request.wallet_address, request.action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Payment action not found")
            
        # 2. Submit to MNEE via Adapter directly (Executor doesn't have a 'submit_only' method yet, using adapter)
        # Note: In a full implementation, we'd add submit_signed_tx to Executor.
        # For now, we use the adapter directly to unblock the hackathon flow.
        
        mnee_adapter = executor.mnee_adapter
        
        try:
            ticket_id = await mnee_adapter.transfer(request.signed_raw_tx)
            
            # 3. Update Action Status
            # We mark it as used/submitted
            await service.mark_used(request.wallet_address, request.action_id)
            
            return PaymentStatusResponse(
                action_id=request.action_id,
                status="submitted",
                ticket_id=ticket_id
            )
            
        except Exception as e:
            logger.error(f"MNEE submission failed: {e}")
            raise HTTPException(status_code=400, detail=f"Submission failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SubmitResultRequest(BaseModel):
    action_id: str
    transaction_hash: str
    wallet_address: str

@router.post("/payments/submit-result", response_model=PaymentStatusResponse)
async def submit_result(
    request: SubmitResultRequest,
    service: PaymentActionService = Depends(get_payment_action_service)
):
    """
    Submit a transaction hash for a completed payment action (broadcasted by frontend).
    """
    try:
        logger.info(f"Received result for action {request.action_id}: {request.transaction_hash}")
        
        # 1. Retrieve the action
        action = await service.get_action(request.wallet_address, request.action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Payment action not found")
            
        # 2. Update Action Status
        await service.mark_used(request.wallet_address, request.action_id)
        
        # We could also store the tx hash in metadata if we wanted
        
        return PaymentStatusResponse(
            action_id=request.action_id,
            status="submitted",
            transaction_hash=request.transaction_hash
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/status/{ticket_id}")
async def get_payment_status(
    ticket_id: str,
    executor: PaymentExecutor = Depends(get_payment_executor)
):
    """Check status of a submitted MNEE ticket."""
    return await executor.get_execution_status(ticket_id)

@router.get("/mnee/transfers/{wallet_address}")
async def get_mnee_transfers(
    wallet_address: str,
    chain_id: int = 1,
    limit: int = 20
):
    """
    Get MNEE transfer history from blockchain for a wallet.
    
    Source of truth: blockchain via Alchemy Asset Transfers API.
    This includes all MNEE transfers (to or from) on the specified chain.
    """
    try:
        from app.services.token_query_service import token_query_service
        
        # Validate address
        if not token_query_service.is_valid_address(wallet_address):
            raise HTTPException(status_code=400, detail="Invalid wallet address")
        
        # Fetch transfers from blockchain
        result = await token_query_service.get_mnee_transfers(
            wallet_address=wallet_address,
            chain_id=chain_id,
            limit=limit
        )
        
        if result.get("source") == "error":
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch transfer history from blockchain"
            )
        
        if result.get("source") == "unavailable":
            logger.warning(
                f"MNEE transfers unavailable for chain {chain_id} or missing config"
            )
            return {"transfers": [], "chain_id": chain_id, "total": 0}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching MNEE transfers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
