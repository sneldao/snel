from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import re
import json

from app.api.dependencies import get_redis_service, get_token_service
from app.agents.dca_agent import DCAAgent
from app.services.dca_service import DCAService
from app.models.transaction import TransactionRequest, TransactionResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dca"])

def humanize_error(error_msg: Optional[Any]) -> Optional[str]:
    """
    Converts technical error messages into user-friendly messages.
    
    Args:
        error_msg: The original error message
        
    Returns:
        A user-friendly error message
    """
    if error_msg is None:
        return None
        
    error_str = str(error_msg)
    
    # Handle validation errors
    if "validation error" in error_str.lower():
        return "There was an issue with the command format. Please try again."
    
    # Handle token not found errors
    if "token not found" in error_str.lower() or "couldn't find token" in error_str.lower():
        return "I couldn't find one of the tokens you specified. Please try again with a different token."
    
    # Handle insufficient balance errors
    if "insufficient balance" in error_str.lower() or "not enough" in error_str.lower():
        return "You don't have enough balance for this transaction."
    
    # Handle general errors in a user-friendly way
    if len(error_str) > 100:
        return "Something went wrong. Please try again."
        
    return error_str

class DCACommand(BaseModel):
    """
    Represents a DCA command sent by a user.
    """
    content: str
    chain_id: int = 1
    wallet_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class DCAResponse(BaseModel):
    """
    Represents a response to a DCA command.
    """
    content: Dict[str, Any]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_type: Optional[str] = "dca"
    pending_command: Optional[str] = None
    transaction: Optional[Dict[str, Any]] = None

class DCAOrderRequest(BaseModel):
    """
    Request to create a DCA order.
    """
    wallet_address: str
    chain_id: int
    token_in_address: str
    token_out_address: str
    amount: float
    frequency: str  # daily, weekly, monthly
    duration: int  # in days

class DCAOrderResponse(BaseModel):
    """
    Response for a DCA order creation.
    """
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class DCACancelRequest(BaseModel):
    """
    Request to cancel a DCA order.
    """
    order_hash: str
    chain_id: int

class DCACancelResponse(BaseModel):
    """
    Response for a DCA order cancellation.
    """
    success: bool
    order_hash: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None

# Dependencies
def get_dca_agent(token_service=Depends(get_token_service)):
    return DCAAgent(token_service=token_service)

def get_dca_service(
    token_service=Depends(get_token_service),
    dca_agent=Depends(get_dca_agent)
):
    return DCAService(token_service=token_service, dca_agent=dca_agent)

@router.post("/process-command", response_model=DCAResponse)
async def process_dca_command(
    command: DCACommand,
    redis_service=Depends(get_redis_service),
    dca_service=Depends(get_dca_service)
):
    """
    Process a DCA command from the user.
    """
    try:
        logger.info(f"Processing DCA command: {command.content}")

        # Check if wallet address is provided
        if not command.wallet_address:
            raise HTTPException(
                status_code=400,
                detail="Wallet address is required for DCA commands"
            )

        # Store the command for reference
        timestamp = datetime.now().isoformat()
        user_id = command.wallet_address
        await redis_service.set(
            f"dca_command_history:{user_id}:{timestamp}",
            {
                "command": command.content,
                "timestamp": timestamp,
                "metadata": command.metadata or {}
            },
            expire=86400  # Store for 24 hours
        )

        # Process the DCA command
        result = await dca_service.process_dca_command(
            command=command.content,
            chain_id=command.chain_id,
            wallet_address=command.wallet_address
        )

        # If there's transaction data in the metadata, store the next step in Redis
        if result.get("metadata", {}).get("next_step") and result.get("metadata", {}).get("transaction"):
            await redis_service.set_pending_command(user_id, command.content)
            await redis_service.set(
                f"dca_next_step:{user_id}",
                result["metadata"]["next_step"],
                expire=3600  # Store for 1 hour
            )

        # Return the response with transaction data if available
        response = DCAResponse(
            content=result.get("content", {}),
            error_message=humanize_error(result.get("error")),
            metadata=result.get("metadata", {}),
            pending_command=command.content if "next_step" in result.get("metadata", {}) else None
        )

        # If there's transaction data, include it in the response
        if result.get("metadata", {}).get("transaction"):
            response.transaction = result["metadata"]["transaction"]

        return response

    except Exception as e:
        logger.exception(f"Error processing DCA command: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process DCA command: {str(e)}"
        ) from e

@router.post("/execute", response_model=TransactionResponse)
async def execute_dca(
    request: TransactionRequest,
    redis_service=Depends(get_redis_service),
    dca_service=Depends(get_dca_service)
) -> TransactionResponse:
    """
    Execute the DCA setup after approval is granted.
    """
    try:
        wallet_address = request.wallet_address
        chain_id = request.chain_id
        
        if not wallet_address:
            raise HTTPException(400, "Missing wallet address")
            
        # Get the next step data
        next_step = await redis_service.get(f"dca_next_step:{wallet_address}")
        if not next_step:
            raise HTTPException(400, "No pending DCA setup found")
        
        # Execute DCA setup
        result = await dca_service.setup_dca_order(
            wallet_address=next_step["wallet_address"],
            chain_id=next_step["chain_id"],
            maker_amount=next_step["maker_amount"],
            taker_amount=next_step["taker_amount"],
            maker_asset=next_step["maker_asset"],
            taker_asset=next_step["taker_asset"],
            frequency_seconds=next_step["frequency_seconds"],
            times=next_step["times"]
        )
        
        if not result.get("success"):
            # Handle error properly - convert dict to string if needed
            error = result.get("error")
            if isinstance(error, dict):
                error = json.dumps(error)
            elif error is None:
                error = "Unknown error setting up DCA order"
                
            return TransactionResponse(
                error=error,
                chain_id=chain_id
            )
        
        # Clean up Redis data
        await redis_service.delete(f"dca_next_step:{wallet_address}")
        
        # Return the transaction response
        return TransactionResponse(
            to=result.get("transaction", {}).get("to"),
            data=result.get("transaction", {}).get("data"),
            value=result.get("transaction", {}).get("value", "0"),
            chain_id=chain_id,
            gas_limit=result.get("transaction", {}).get("gas_limit"),
            gas_price=result.get("transaction", {}).get("gas_price"),
            max_fee_per_gas=result.get("transaction", {}).get("max_fee_per_gas"),
            max_priority_fee_per_gas=result.get("transaction", {}).get("max_priority_fee_per_gas"),
            method="dca_setup",
            metadata=result.get("metadata", {})
        )
        
    except Exception as e:
        logger.error(f"Error executing DCA setup: {str(e)}")
        return TransactionResponse(
            error=str(e),
            chain_id=chain_id
        )

@router.post("/create-order", response_model=DCAOrderResponse)
async def create_dca_order(
    request: DCAOrderRequest,
    dca_service=Depends(get_dca_service),
    token_service=Depends(get_token_service)
):
    """
    Create a new DCA order.
    """
    try:
        # Get token information
        token_in_info = await token_service.get_token_info(request.token_in_address, request.chain_id)
        token_out_info = await token_service.get_token_info(request.token_out_address, request.chain_id)
        
        if not token_in_info or not token_out_info:
            raise HTTPException(
                status_code=400,
                detail="Invalid token addresses"
            )
        
        # Create the DCA order
        result = await dca_service.create_dca_order(
            wallet_address=request.wallet_address,
            chain_id=request.chain_id,
            token_in=token_in_info,
            token_out=token_out_info,
            amount=request.amount,
            frequency=request.frequency,
            duration=request.duration
        )
        
        # Check for error
        if not result["success"]:
            return DCAOrderResponse(
                success=False,
                error=result.get("error", "Unknown error creating DCA order")
            )
        
        # Return the response
        return DCAOrderResponse(
            success=True,
            order_id=result.get("order_id"),
            details=result.get("details")
        )
            
    except Exception as e:
        logger.exception(f"Error creating DCA order: {e}")
        return DCAOrderResponse(
            success=False,
            error=f"Failed to create DCA order: {str(e)}"
        )

@router.post("/cancel-order", response_model=DCACancelResponse)
async def cancel_dca_order(
    request: DCACancelRequest,
    dca_service=Depends(get_dca_service)
):
    """
    Cancel a DCA order.
    """
    try:
        # Cancel the DCA order
        result = await dca_service.cancel_dca_order(
            order_hash=request.order_hash,
            chain_id=request.chain_id
        )
        
        # Check for error
        if not result["success"]:
            return DCACancelResponse(
                success=False,
                error=result.get("error", "Unknown error cancelling DCA order")
            )
        
        # Return the response
        return DCACancelResponse(
            success=True,
            order_hash=result.get("order_hash"),
            status=result.get("status")
        )
            
    except Exception as e:
        logger.exception(f"Error cancelling DCA order: {e}")
        return DCACancelResponse(
            success=False,
            error=f"Failed to cancel DCA order: {str(e)}"
        )

@router.get("/orders/{wallet_address}/{chain_id}", response_model=Dict[str, Any])
async def get_dca_orders(
    wallet_address: str,
    chain_id: int,
    limit: int = 10,
    dca_service=Depends(get_dca_service)
):
    """
    Get DCA orders for a wallet address.
    """
    try:
        # Get the orders
        result = await dca_service.get_dca_orders(
            wallet_address=wallet_address,
            chain_id=chain_id,
            limit=limit
        )
        
        # Return the result
        return result
            
    except Exception as e:
        logger.exception(f"Error getting DCA orders: {e}")
        return {
            "success": False,
            "error": f"Failed to get DCA orders: {str(e)}"
        } 