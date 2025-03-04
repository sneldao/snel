from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.models.transaction import TransactionRequest, TransactionResponse
from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.redis_service import RedisService, get_redis_service
from app.agents.simple_swap_agent import SimpleSwapAgent

router = APIRouter(tags=["swap"])
logger = logging.getLogger(__name__)

# Model for swap quote selection
class QuoteSelectionRequest(BaseModel):
    wallet_address: str
    chain_id: int = 1
    quote_index: int
    pending_command: str

# Model for swap command
class SwapCommand(BaseModel):
    command: str
    wallet_address: str
    chain_id: int = 1

def create_swap_services(token_service: TokenService) -> SwapService:
    """Create and return SwapService instance with dependencies."""
    swap_agent = SimpleSwapAgent()
    return SwapService(token_service=token_service, swap_agent=swap_agent)

@router.post("/process-command", response_model=Dict[str, Any])
async def process_swap_command(
    swap_command: SwapCommand, 
    redis_service: RedisService = Depends(get_redis_service)
) -> Dict[str, Any]:
    """
    Process a swap command from natural language.
    Returns token information for confirmation.
    """
    try:
        command = swap_command.command
        wallet_address = swap_command.wallet_address
        chain_id = swap_command.chain_id
        
        logger.info(f"Processing swap command: {command} for wallet {wallet_address} on chain {chain_id}")
        
        if not command or not wallet_address:
            raise HTTPException(400, "Missing command or wallet address")
            
        # Store command in redis for later use
        try:
            logger.info(f"Storing command in Redis: {command}")
            await redis_service.set_pending_command(wallet_address, command)
            logger.info("Command stored successfully")
        except Exception as redis_error:
            logger.error(f"Error storing command in Redis: {str(redis_error)}")
            # Continue even if Redis fails
        
        # Get token information
        token_service = TokenService()
        swap_agent = SimpleSwapAgent()
        
        logger.info("Calling swap_agent.process_swap_command")
        try:
            result = await swap_agent.process_swap_command(command, chain_id)
            logger.info(f"Swap agent result: {result}")
        except Exception as agent_error:
            logger.error(f"Error in swap agent: {str(agent_error)}")
            raise
        
        # Format for frontend display via SwapConfirmation component
        return result
    except Exception as e:
        logger.error(f"Error processing swap command: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@router.post("/get-quotes", response_model=Dict[str, Any])
async def get_swap_quotes(
    request: dict,
    redis_service: RedisService = Depends(get_redis_service)
) -> Dict[str, Any]:
    """
    After user confirms the tokens, get quotes from various aggregators.
    Returns quotes for user selection.
    """
    try:
        wallet_address = request.get("wallet_address", "")
        chain_id = request.get("chain_id", 1)
        
        if not wallet_address:
            raise HTTPException(400, "Missing wallet address")
            
        # Get pending command
        pending_command = await redis_service.get_pending_command(wallet_address)
        if not pending_command:
            raise HTTPException(400, "No pending swap command found")
        
        # Get quotes
        token_service = TokenService()
        swap_service = create_swap_services(token_service)
        
        try:
            quotes = await swap_service.get_swap_quotes(pending_command, chain_id, wallet_address)
            return quotes
        except Exception as e:
            logger.error(f"Error getting swap quotes: {str(e)}")
            return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error getting swap quotes: {str(e)}")
        return {"error": str(e)}

@router.post("/execute", response_model=TransactionResponse)
async def execute_swap(
    request: TransactionRequest,
    redis_service: RedisService = Depends(get_redis_service)
) -> TransactionResponse:
    """
    Execute the selected swap quote.
    Returns transaction data for signing and sending.
    """
    try:
        wallet_address = request.wallet_address
        chain_id = request.chain_id
        selected_quote = request.selected_quote
        
        if not wallet_address or not selected_quote:
            raise HTTPException(400, "Missing wallet address or selected quote")
            
        # Get pending command
        pending_command = await redis_service.get_pending_command(wallet_address)
        if not pending_command:
            raise HTTPException(400, "No pending swap command found")
        
        # Execute swap
        token_service = TokenService()
        swap_service = create_swap_services(token_service)
        
        tx_data = await swap_service.build_transaction_from_quote(
            wallet_address=wallet_address,
            chain_id=chain_id,
            selected_quote=selected_quote,
            pending_command=pending_command
        )
        
        return TransactionResponse(
            to=tx_data.get("to"),
            data=tx_data.get("data"),
            value=tx_data.get("value"),
            chain_id=chain_id,
            gas_limit=tx_data.get("gas_limit"),
            gas_price=tx_data.get("gas_price"),
            max_fee_per_gas=tx_data.get("max_fee_per_gas"),
            max_priority_fee_per_gas=tx_data.get("max_priority_fee_per_gas"),
            method="swap",
            metadata=tx_data.get("metadata", {})
        )
    except Exception as e:
        logger.error(f"Error executing swap: {str(e)}")
        return TransactionResponse(
            error=str(e),
            chain_id=chain_id
        )

# Add these to main.py router includes
# app.include_router(swap_router.router, prefix="/api")
