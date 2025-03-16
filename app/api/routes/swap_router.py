from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.models.transaction import TransactionRequest, TransactionResponse
from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.redis_service import RedisService, get_redis_service
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.services.scroll_handler import ScrollHandler
from app.models.commands import SwapCommand as SwapCommandModel

router = APIRouter(tags=["swap"])
logger = logging.getLogger(__name__)

# Model for swap quote selection
class QuoteSelectionRequest(BaseModel):
    wallet_address: str
    chain_id: int = 1
    quote_index: int
    pending_command: str

# Model for swap command request
class SwapCommandRequest(BaseModel):
    command: str
    wallet_address: str
    chain_id: int = 1

def create_swap_services(token_service: TokenService) -> SwapService:
    """Create and return SwapService instance with dependencies."""
    swap_agent = SimpleSwapAgent()
    return SwapService(token_service=token_service, swap_agent=swap_agent)

@router.post("/process-command", response_model=Dict[str, Any])
async def process_swap_command(
    swap_command: SwapCommandRequest, 
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
            
            # Check for errors in the result
            if result.get("error"):
                logger.error(f"Error from swap agent: {result['error']}")
                return {
                    "error": result["error"],
                    "content": None,
                    "metadata": result.get("metadata", {})
                }
            
            # Format for frontend display via SwapConfirmation component
            return result
        except Exception as agent_error:
            logger.error(f"Error in swap agent: {str(agent_error)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "error": f"Error processing swap: {str(agent_error)}",
                "content": None,
                "metadata": {"command": command}
            }
    except Exception as e:
        logger.error(f"Error processing swap command: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "error": f"Error processing swap: {str(e)}",
            "content": None,
            "metadata": {"command": command if 'command' in locals() else "unknown"}
        }

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
            # For Scroll chain, use only Brian API
            if chain_id == 534352:  # Scroll chain ID
                logger.info("Handling Scroll chain quotes - using Brian API exclusively")
                
                # Parse the swap command to get a SwapCommand object
                swap_command = await swap_service.parse_swap_command(pending_command, chain_id, wallet_address)
                
                if not isinstance(swap_command, SwapCommandModel):
                    raise ValueError(f"Failed to parse swap command: {pending_command}")
                
                # Get transaction data from Brian API
                brian_tx_data = await ScrollHandler.use_brian_api(
                    swap_command=swap_command,
                    wallet_address=wallet_address,
                    chain_id=chain_id
                )
                
                if brian_tx_data and brian_tx_data.get("all_quotes"):
                    # Extract token information
                    token_in_info = await token_service.lookup_token(
                        swap_command.token_in, chain_id
                    )
                    token_out_info = await token_service.lookup_token(
                        swap_command.token_out, chain_id
                    )
                    
                    # Extract token info (address, symbol, name, metadata)
                    from_address, from_symbol, from_name, from_metadata = token_in_info
                    to_address, to_symbol, to_name, to_metadata = token_out_info
                    
                    # Get token decimals
                    from_decimals = await token_service.get_token_decimals(from_address, chain_id)
                    to_decimals = await token_service.get_token_decimals(to_address, chain_id)
                    
                    # Format quotes for frontend
                    formatted_quotes = []
                    
                    for quote in brian_tx_data["all_quotes"]:
                        if quote.get("is_approval", False):
                            continue
                            
                        formatted_quotes.append({
                            "aggregator": "brian",
                            "protocol": "Brian API",
                            "buy_amount": quote.get("buy_amount", "0"),
                            "minimum_received": quote.get("buy_amount", "0"),  # Will be adjusted with slippage later
                            "gas_usd": "0",
                            "gas": quote.get("gas", "500000"),
                            "to": quote.get("to", ""),
                            "data": quote.get("data", ""),
                            "value": quote.get("value", "0"),
                            "token_in_symbol": from_symbol,
                            "token_in_decimals": from_decimals,
                            "token_out_symbol": to_symbol,
                            "token_out_decimals": to_decimals
                        })
                    
                    # Return quotes with Brian API note
                    return {
                        "quotes": formatted_quotes,
                        "token_in": {
                            "address": from_address,
                            "symbol": from_symbol,
                            "name": from_name,
                            "metadata": from_metadata
                        },
                        "token_out": {
                            "address": to_address,
                            "symbol": to_symbol,
                            "name": to_name,
                            "metadata": to_metadata
                        },
                        "amount": float(swap_command.amount_in),
                        "amount_is_usd": swap_command.amount_is_usd,
                        "scroll_note": "Using Brian API for Scroll swaps"
                    }
                else:
                    # If Brian API fails, return an error
                    raise ValueError("Brian API is required for Scroll swaps but is currently unavailable. Please ensure BRIAN_API_KEY is set in your environment variables.")
            else:
                # For other chains, use regular aggregators
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
        
        # For Scroll chain, use only Brian API
        if chain_id == 534352:  # Scroll chain ID
            logger.info("Handling Scroll chain transaction - using Brian API exclusively")
            
            # Parse the swap command
            swap_command = await swap_service.parse_swap_command(pending_command, chain_id, wallet_address)
            
            if not isinstance(swap_command, SwapCommandModel):
                raise HTTPException(400, "Failed to parse swap command")
            
            # Get transaction data from Brian API
            brian_tx_data = await ScrollHandler.use_brian_api(
                swap_command=swap_command,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            
            if brian_tx_data and brian_tx_data.get("all_quotes"):
                # Use the first non-approval quote from Brian API
                brian_quote = next((q for q in brian_tx_data["all_quotes"] if not q.get("is_approval")), None)
                if brian_quote:
                    logger.info("Using Brian API quote for transaction")
                    tx_data = {
                        "to": brian_quote["to"],
                        "data": brian_quote["data"],
                        "value": brian_quote["value"],
                        "gas_limit": brian_quote.get("gas", "500000"),
                        "method": "swap",
                        "metadata": {
                            **brian_tx_data.get("metadata", {}),
                            "aggregator": "brian",
                            "protocol": "Brian API"
                        }
                    }
                    
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
                else:
                    raise HTTPException(400, "No valid quote found from Brian API")
            else:
                raise HTTPException(400, "Brian API is required for Scroll swaps but is currently unavailable")
        else:
            # For other chains, use regular flow
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
        
        # Apply Scroll-specific error handling if on Scroll chain
        error_message = str(e)
        if chain_id == 534352:  # Scroll chain ID
            error_message = ScrollHandler.handle_scroll_error(error_message, chain_id)
        
        return TransactionResponse(
            error=error_message,
            chain_id=chain_id
        )

# Add these to main.py router includes
# app.include_router(swap_router.router, prefix="/api")
