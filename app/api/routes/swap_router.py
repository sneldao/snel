from fastapi import APIRouter, Depends, Request, HTTPException
import logging
from typing import Dict, Optional, Any
import os

from app.models.commands import TransactionRequest, TransactionResponse
from app.config.chains import ChainConfig
from app.services.token_service import TokenService
from app.api.dependencies import get_token_service, get_swap_service, get_openai_key
from app.utils.error_handling import (
    handle_exception, 
    safe_execute_async, 
    ErrorResponse, 
    ErrorCode
)

from emp_agents.providers import OpenAIProvider
from app.config.settings import settings
from app.agents.swap_agent import SwapAgent
from app.services.swap_service import SwapService, NoRouteFoundError, InsufficientLiquidityError, InvalidTokenError, TransferFromFailedError
from app.services.transaction_executor import SPECIAL_TOKENS_LOWER

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

def create_swap_services(token_service: TokenService) -> SwapService:
    """Create SwapAgent and SwapService."""
    provider = OpenAIProvider(api_key=settings.openai_api_key)
    swap_agent = SwapAgent(provider=provider)
    return SwapService(token_service=token_service, swap_agent=swap_agent)

@router.post("/execute", response_model=TransactionResponse)
async def execute_transaction(
    tx_request: TransactionRequest,
    request: Request
):
    """
    Execute a transaction based on a natural language command.
    
    This is the primary endpoint for transaction execution.
    """
    try:
        logger.info(f"Executing transaction for command: {tx_request.command} on chain {tx_request.chain_id}")
        
        # Get dependencies directly
        token_service = TokenService()
        
        # Get OpenAI API key from request headers or environment
        openai_api_key = request.headers.get("X-OpenAI-Key")
        if not openai_api_key:
            # Fallback to environment variable
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                raise HTTPException(
                    status_code=401,
                    detail="OpenAI API Key is required (either in header or environment)"
                )
        
        # Create services directly
        provider = OpenAIProvider(api_key=openai_api_key)
        swap_agent = SwapAgent(provider=provider)
        swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
        
        # Validate chain support
        if not ChainConfig.is_supported(tx_request.chain_id):
            supported_chains = ', '.join(f'{name} ({id})' for id, name in ChainConfig.SUPPORTED_CHAINS.items())
            raise ValueError(f"Chain {tx_request.chain_id} is not supported. Supported chains: {supported_chains}")

        # For swap commands, process the transaction
        if tx_request.command.startswith("swap ") or tx_request.command.startswith("approved:"):
            logger.info(f"Processing swap command: {tx_request.command}")
            
            try:
                # Call the process_swap_command method directly
                tx_data = await swap_service.process_swap_command(
                    command=tx_request.command,
                    chain_id=tx_request.chain_id,
                    wallet_address=tx_request.wallet_address,
                    skip_approval=tx_request.skip_approval
                )
            except NoRouteFoundError as e:
                logger.error(f"No route found for swap: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail={"error": str(e), "code": "NO_ROUTE_FOUND", "message": "No valid route found for this swap. Try different tokens or amounts."}
                )
            except InsufficientLiquidityError as e:
                logger.error(f"Insufficient liquidity for swap: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail={"error": str(e), "code": "INSUFFICIENT_LIQUIDITY", "message": "There isn't enough liquidity for this swap. Try using a smaller amount or a different token pair."}
                )
            except InvalidTokenError as e:
                logger.error(f"Invalid token error: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail={"error": str(e), "code": "INVALID_TOKEN", "message": "One or more tokens in your swap are invalid or not supported on this chain."}
                )
            except TransferFromFailedError as e:
                logger.error(f"Transfer failed error: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail={"error": str(e), "code": "TRANSFER_FAILED", "message": "Failed to transfer token. Check your balances and token approvals."}
                )
            except Exception as e:
                logger.error(f"Error processing swap command: {e}")
                http_exception = handle_exception(e)
                raise http_exception
            
            if isinstance(tx_data, ErrorResponse):
                raise HTTPException(status_code=400, detail=tx_data.dict())
            
            if "error" in tx_data:
                error_msg = tx_data["error"]
                
                # Check for common error patterns and provide better messages
                if "gas required exceeds allowance" in error_msg.lower():
                    error_msg = "This token has special mechanics that require higher gas. Try increasing the gas limit or using a smaller amount."
                elif "price impact too high" in error_msg.lower():
                    error_msg = "The price impact for this swap is too high. Try using a smaller amount or a different token pair."
                elif "insufficient liquidity" in error_msg.lower():
                    error_msg = "There isn't enough liquidity for this swap. Try using a smaller amount or a different token pair."
                elif "cannot estimate gas" in error_msg.lower() or "failed to estimate gas" in error_msg.lower():
                    error_msg = "Unable to estimate gas for this swap. This usually happens with tokens that have special transfer mechanics. Try a smaller amount or contact the token's community for guidance."
                
                raise HTTPException(
                    status_code=400, 
                    detail={"error": error_msg, "code": "TRANSACTION_FAILED", "message": error_msg}
                )
            
            # Check if we're dealing with a special token (either input or output)
            token_in_address = tx_data.get("from_token_address", "").lower()
            token_out_address = tx_data.get("to_token_address", "").lower() 
            router_address = tx_data.get("to", "").lower()
            
            special_token_info = None
            special_token_address = None
            
            if token_in_address in SPECIAL_TOKENS_LOWER:
                special_token_info = SPECIAL_TOKENS_LOWER[token_in_address]
                special_token_address = token_in_address
            elif token_out_address in SPECIAL_TOKENS_LOWER:
                special_token_info = SPECIAL_TOKENS_LOWER[token_out_address]
                special_token_address = token_out_address
            
            # Add special token handling
            if special_token_info:
                logger.info(f"Special token detected: {special_token_info['name']} at {special_token_address}")
                
                # Add warning to metadata
                if "metadata" not in tx_data:
                    tx_data["metadata"] = {}
                
                tx_data["metadata"]["warning"] = special_token_info["warning"]
                tx_data["metadata"]["suggestion"] = special_token_info["suggestion"]
                
                # Increase gas limit for special tokens
                if "gas_limit" in tx_data:
                    current_gas = int(tx_data["gas_limit"]) if isinstance(tx_data["gas_limit"], str) and not tx_data["gas_limit"].startswith("0x") else int(tx_data["gas_limit"], 16)
                    new_gas = int(current_gas * special_token_info.get("gas_multiplier", 1.5))
                    logger.info(f"Increasing gas limit for special token from {current_gas} to {new_gas}")
                    tx_data["gas_limit"] = new_gas
                
                # Add special token info to metadata
                tx_data["metadata"]["special_token"] = True
                tx_data["metadata"]["special_token_name"] = special_token_info["name"]
                tx_data["metadata"]["max_recommended_amount"] = special_token_info.get("max_amount", "5")
            
            # Ensure required fields are present
            required_fields = ["to", "data", "value"]
            for field in required_fields:
                if field not in tx_data:
                    raise HTTPException(
                        status_code=400,
                        detail={"error": f"Missing required field: {field}", "code": "MISSING_FIELD"}
                    )

            # Log the transaction data for debugging
            logger.info(f"Transaction data prepared: to={tx_data['to']}, gas_limit={tx_data.get('gas_limit')}, value={tx_data.get('value')}")
            
            # Return the transaction data
            return TransactionResponse(
                to=tx_data["to"],
                data=tx_data["data"],
                value=tx_data["value"],
                chain_id=tx_request.chain_id,
                method=tx_data.get("method", "swap"),
                gas_limit=tx_data["gas_limit"],
                gas_price=tx_data.get("gas_price"),
                max_fee_per_gas=tx_data.get("max_fee_per_gas"),
                max_priority_fee_per_gas=tx_data.get("max_priority_fee_per_gas"),
                needs_approval=tx_data.get("needs_approval", False),
                token_to_approve=tx_data.get("token_to_approve"),
                spender=tx_data.get("spender"),
                pending_command=tx_data.get("pending_command", tx_request.command),
                metadata=tx_data.get("metadata", {}),
                agent_type="swap"  # Always swap for transactions
            )

        # If not a swap command, handle other transaction types
        raise ValueError("Unsupported transaction type")

    except HTTPException:
        # Re-raise HTTPExceptions as they're already properly formatted
        raise
    except Exception as e:
        # Use handle_exception to standardize the error
        http_exception = handle_exception(e)
        raise http_exception
