from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
import uuid

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
            await redis_service.store_pending_command(
                wallet_address=wallet_address,
                command=command,
                is_brian_operation=False  # Explicitly mark as NOT a Brian operation
            )
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

        # Check if this is a Brian operation and skip swap quotes if it is
        is_brian_operation = False
        command_text = pending_command
        
        if isinstance(pending_command, dict):
            is_brian_operation = pending_command.get("is_brian_operation", False)
            command_text = pending_command.get("command", "")
        elif isinstance(pending_command, str):
            command_text = pending_command
        else:
            # Handle unexpected pending_command format
            raise HTTPException(400, f"Invalid pending command format: {type(pending_command)}")
        
        if is_brian_operation:
            logger.info(f"Skipping swap quotes for Brian operation: {command_text}")
            return {
                "message": "Brian operation does not require swap quotes",
                "is_brian_operation": True
            }

        # Verify we have a valid command string
        if not command_text or not isinstance(command_text, str) or len(command_text) < 3:
            raise HTTPException(400, "Invalid or empty pending swap command")
            
        logger.info(f"Processing swap quotes for command: {command_text}")

        # Get quotes
        token_service = TokenService()
        swap_service = create_swap_services(token_service)

        try:
            # For Scroll chain, use only Brian API
            if chain_id == 534352:  # Scroll chain ID
                logger.info("Handling Scroll chain quotes - using Brian API exclusively")

                # Parse the swap command to get a SwapCommand object
                swap_command = await swap_service.parse_swap_command(command_text, chain_id, wallet_address)

                if not isinstance(swap_command, SwapCommandModel):
                    raise ValueError(f"Failed to parse swap command: {command_text}")

                # Get transaction data from Brian API
                brian_tx_data = await ScrollHandler.use_brian_api(
                    swap_command=swap_command,
                    wallet_address=wallet_address,
                    chain_id=chain_id
                )

                if not brian_tx_data or not brian_tx_data.get("all_quotes"):
                    # If Brian API fails, return an error
                    raise ValueError("Brian API is required for Scroll swaps but is currently unavailable. Please ensure BRIAN_API_KEY is set in your environment variables.")
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

                formatted_quotes = [
                    {
                        "aggregator": "brian",
                        "protocol": "Brian API",
                        "buy_amount": quote.get("buy_amount", "0"),
                        "minimum_received": quote.get(
                            "buy_amount", "0"
                        ),  # Will be adjusted with slippage later
                        "gas_usd": "0",
                        "gas": quote.get("gas", "500000"),
                        "to": quote.get("to", ""),
                        "data": quote.get("data", ""),
                        "value": quote.get("value", "0"),
                        "token_in_symbol": from_symbol,
                        "token_in_decimals": from_decimals,
                        "token_out_symbol": to_symbol,
                        "token_out_decimals": to_decimals,
                    }
                    for quote in brian_tx_data["all_quotes"]
                    if not quote.get("is_approval", False)
                ]
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
                # For other chains, use regular aggregators
                quotes = await swap_service.get_swap_quotes(command_text, chain_id, wallet_address)
                return quotes

        except Exception as e:
            logger.error(f"Error getting swap quotes: {str(e)}")
            return {
                "error": str(e),
                "status": "error",
                "message": f"Failed to get swap quotes: {str(e)}"
            }
    except Exception as e:
        logger.error(f"Error getting swap quotes: {str(e)}")
        return {"error": str(e)}

@router.post("/execute", response_model=TransactionResponse)
async def execute_swap(
    request: Dict[str, Any], 
    redis_service: RedisService = Depends(get_redis_service)
) -> TransactionResponse:
    """
    Execute a swap transaction.
    """
    try:
        request_id = str(uuid.uuid4())[:8]
        wallet_address = request.get("wallet_address")
        chain_id = request.get("chain_id", 1)
        selected_quote = request.get("selected_quote")
        
        if not wallet_address:
            return TransactionResponse(
                error="Wallet address is required",
                status="error"
            )
        
        logger.info(f"[{request_id}] Swap execution requested for wallet {wallet_address} on chain {chain_id}")
        
        try:
            # Get the pending command
            pending_data = await redis_service.get_pending_command(wallet_address)
            logger.info(f"[{request_id}] Retrieved pending command: {pending_data}")
            
            # Extract the actual command text from the data
            pending_command = pending_data
            if isinstance(pending_data, dict) and "command" in pending_data:
                pending_command = pending_data["command"]
            
            # Create token service
            token_service = TokenService()
            swap_service = create_swap_services(token_service)
            
            # For Scroll chain, use only Brian API
            if chain_id == 534352:  # Scroll chain ID
                logger.info(f"[{request_id}] Handling Scroll chain transaction - using Brian API exclusively")
                
                try:
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
                    
                    # Extract token data for metadata
                    token_in_info = await token_service.lookup_token(
                        swap_command.token_in, chain_id
                    )
                    token_out_info = await token_service.lookup_token(
                        swap_command.token_out, chain_id
                    )
                    
                    # Format metadata
                    metadata = {
                        "token_in_address": token_in_info[0] if token_in_info else None,
                        "token_in_symbol": token_in_info[1] if token_in_info else None,
                        "token_in_name": token_in_info[2] if token_in_info else None,
                        "token_out_address": token_out_info[0] if token_out_info else None,
                        "token_out_symbol": token_out_info[1] if token_out_info else None,
                        "token_out_name": token_out_info[2] if token_out_info else None
                    }
                    
                    # Use Brian quote as the selected quote
                    selected_quote = brian_tx_data["all_quotes"][0]
                    
                    # Return transaction data
                    return TransactionResponse(
                        to=selected_quote["to"],
                        data=selected_quote["data"],
                        value=selected_quote["value"],
                        gas_limit=selected_quote.get("gas", "500000"),
                        chain_id=chain_id,
                        method="swap",
                        metadata=metadata,
                        agent_type="swap"
                    )
                except Exception as e:
                    logger.error(f"[{request_id}] Error executing Scroll swap: {str(e)}")
                    raise ValueError(f"Error executing Scroll swap: {str(e)}")
            else:
                # For other chains
                # Get transaction data based on selected quote
                tx_data = await swap_service.get_swap_transaction(
                    pending_command, 
                    chain_id, 
                    wallet_address, 
                    selected_quote
                )
                
                if tx_data.get("error"):
                    raise ValueError(tx_data["error"])
                
                # Return transaction data
                return TransactionResponse(
                    to=tx_data["to"],
                    data=tx_data["data"],
                    value=tx_data["value"],
                    gas_limit=tx_data.get("gas_limit", "500000"),
                    gas_price=tx_data.get("gas_price"),
                    max_fee_per_gas=tx_data.get("max_fee_per_gas"),
                    max_priority_fee_per_gas=tx_data.get("max_priority_fee_per_gas"),
                    chain_id=chain_id,
                    method="swap",
                    metadata=tx_data.get("metadata", {})
                )
        except Exception as e:
            logger.error(f"[{request_id}] Error executing swap: {str(e)}")
            raise ValueError(f"Error executing swap: {str(e)}")
    except ValueError as e:
        logger.error(f"Error executing swap: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error"
        )
    except Exception as e:
        logger.error(f"Unexpected error executing swap: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error"
        )

# Add these to app/main.py router includes
