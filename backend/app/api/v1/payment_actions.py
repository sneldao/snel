"""
Payment Actions API - Manage recurring and template payments.

Endpoints for CRUD operations on user payment actions.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.domains.payment_actions.service import get_payment_action_service
from app.domains.payment_actions.models import (
    PaymentAction,
    UpdatePaymentActionRequest,
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/payment-actions", tags=["payment-actions"])


class PaymentActionResponse(BaseModel):
    """Response model for payment action."""
    id: str
    name: str
    action_type: str
    amount: str
    token: str
    recipient_address: Optional[str] = None
    is_enabled: bool
    created_at: str
    last_used: Optional[str] = None
    usage_count: int


@router.get("", response_model=List[PaymentActionResponse])
async def list_payment_actions(
    wallet_address: Optional[str] = Depends(get_current_user),
):
    """Get all payment actions for the user."""
    if not wallet_address:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        service = await get_payment_action_service()
        actions = await service.get_actions(wallet_address)
        
        return [
            PaymentActionResponse(
                id=a.id,
                name=a.name,
                action_type=a.action_type.value,
                amount=a.amount,
                token=a.token,
                recipient_address=a.recipient_address,
                is_enabled=a.is_enabled,
                created_at=a.created_at.isoformat() if a.created_at else None,
                last_used=a.last_used.isoformat() if a.last_used else None,
                usage_count=a.usage_count,
            )
            for a in actions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{action_id}", response_model=PaymentActionResponse)
async def get_payment_action(
    action_id: str,
    wallet_address: Optional[str] = Depends(get_current_user),
):
    """Get a specific payment action."""
    if not wallet_address:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        service = await get_payment_action_service()
        action = await service.get_action(wallet_address, action_id)
        
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        return PaymentActionResponse(
            id=action.id,
            name=action.name,
            action_type=action.action_type.value,
            amount=action.amount,
            token=action.token,
            recipient_address=action.recipient_address,
            is_enabled=action.is_enabled,
            created_at=action.created_at.isoformat() if action.created_at else None,
            last_used=action.last_used.isoformat() if action.last_used else None,
            usage_count=action.usage_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{action_id}")
async def update_payment_action(
    action_id: str,
    request: UpdatePaymentActionRequest,
    wallet_address: Optional[str] = Depends(get_current_user),
):
    """Update a payment action."""
    if not wallet_address:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        service = await get_payment_action_service()
        
        # Verify action belongs to user
        action = await service.get_action(wallet_address, action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        # Update the action
        updated = await service.update_action(wallet_address, action_id, request)
        
        if not updated:
            raise HTTPException(status_code=400, detail="Failed to update action")
        
        return {
            "status": "success",
            "id": updated.id,
            "is_enabled": updated.is_enabled,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{action_id}")
async def delete_payment_action(
    action_id: str,
    wallet_address: Optional[str] = Depends(get_current_user),
):
    """Delete a payment action."""
    if not wallet_address:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        service = await get_payment_action_service()
        
        # Verify action belongs to user
        action = await service.get_action(wallet_address, action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        # Delete the action
        deleted = await service.delete_action(wallet_address, action_id)
        
        if not deleted:
            raise HTTPException(status_code=400, detail="Failed to delete action")
        
        return {"status": "success", "id": action_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
