"""
Swap aggregator endpoints using the protocol registry architecture.
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from decimal import Decimal
from app.services.swap_service import swap_service
from app.services.token_service import token_service
from app.services.transaction_flow_service import transaction_flow_service
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swap", tags=["swap"])

# In-memory store for last swap per wallet
last_swaps: Dict[str, Dict[str, Any]] = {}

# Request/Response models
class SwapCommand(BaseModel):
    command: str = Field(description="Swap command string")
    wallet_address: str = Field(description="User wallet address")
    chain_id: int = Field(description="Current chain ID")

class SwapQuotesRequest(BaseModel):
    wallet_address: str = Field(description="User wallet address")
    chain_id: int = Field(description="Current chain ID")

class SwapQuoteResponse(BaseModel):
    protocol: str
    rate: float
    gas_cost_usd: Optional[float] = Field(default=None)
    from_amount_usd: Optional[float] = Field(default=None)
    to_amount_usd: Optional[float] = Field(default=None)
    gas_limit: Optional[str] = Field(default=None)
    gas_price: Optional[str] = Field(default=None)
    steps: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)

# This function is no longer needed - token_service handles formatting

# Simplified token resolution using scalable token service
async def resolve_token_enhanced(chain_id: int, token_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Scalable token resolution using the token service.
    Handles common tokens, token lists, and on-chain resolution automatically.
    """
    token_info = await token_service.get_token_info(chain_id, token_identifier)
    if token_info:
        return {
            "address": token_info.get("address", ""),
            "symbol": token_info.get("symbol", token_identifier.upper()),
            "name": token_info.get("name", token_identifier.upper()),
            "metadata": token_info.get("metadata", {
                "verified": False,
                "source": "unknown",
                "decimals": 18
            })
        }

    return None

# 1. Parse and confirm swap command
@router.post("/process-command")
async def process_swap_command(cmd: SwapCommand) -> Dict[str, Any]:
    """Process a swap command from the user."""
    # Check if this is a confirmation
    if cmd.command.lower().strip() == "yes":
        meta = last_swaps.get(cmd.wallet_address)
        if not meta:
            return {
                "success": False,
                "message": "No pending swap to confirm",
                "error_details": {
                    "error": "No pending swap to confirm",
                    "suggestion": "Please submit a swap request before confirming.",
                    "protocols_tried": []
                }
            }

        # Check if user switched networks since the initial swap request
        stored_chain_id = meta.get("chain_id")
        if stored_chain_id and stored_chain_id != cmd.chain_id:
            # Clear the pending swap since network changed
            del last_swaps[cmd.wallet_address]

            # Get chain names for user-friendly message
            chain_names = {
                1: "Ethereum", 42161: "Arbitrum One", 137: "Polygon", 10: "Optimism",
                56: "BNB Chain", 43114: "Avalanche", 8453: "Base", 534352: "Scroll",
                324: "zkSync Era", 59144: "Linea", 5000: "Mantle", 81457: "Blast"
            }
            old_chain_name = chain_names.get(stored_chain_id, f"Chain {stored_chain_id}")
            new_chain_name = chain_names.get(cmd.chain_id, f"Chain {cmd.chain_id}")

            return {
                "success": False,
                "message": f"Network changed from {old_chain_name} to {new_chain_name}. Please start a new swap request.",
                "error_details": {
                    "error": f"Network changed from {old_chain_name} to {new_chain_name}. Please start a new swap request.",
                    "suggestion": f"You switched from {old_chain_name} to {new_chain_name}. Please submit a new swap command for the current network.",
                    "protocols_tried": [],
                    "network_change": True,
                    "old_chain_id": stored_chain_id,
                    "new_chain_id": cmd.chain_id
                }
            }

        # Get quote and build transaction for the confirmed swap
        try:
            # First get the quote
            quote_result = await swap_service.get_quote(
                from_token_id=meta["from_token"],
                to_token_id=meta["to_token"],
                amount=Decimal(meta["amount"]),
                chain_id=cmd.chain_id,
                wallet_address=cmd.wallet_address
            )

            # Check for errors in quote
            if "error" in quote_result:
                return {
                    "success": False,
                    "message": quote_result["error"],
                    "error_details": {
                        "error": quote_result["error"],
                        "technical_details": quote_result.get("technical_details", ""),
                        "protocols_tried": quote_result.get("protocols_tried", []),
                        "suggestion": quote_result.get("suggestion", "Please try again in a few moments.")
                    }
                }

            # Check if this is a multi-step transaction
            requires_multi_step = quote_result.get("requires_multi_step", False)
            all_steps = quote_result.get("steps", [])

            if requires_multi_step and all_steps:
                # Create transaction flow for multi-step execution
                flow = transaction_flow_service.create_flow(
                    wallet_address=cmd.wallet_address,
                    chain_id=cmd.chain_id,
                    operation_type="swap",
                    steps_data=all_steps,
                    metadata={
                        "from_token": meta["from_token"],
                        "to_token": meta["to_token"],
                        "amount": meta["amount"],
                        "protocol": quote_result.get("protocol", "unknown"),
                        "quote_metadata": quote_result.get("metadata", {})
                    }
                )

                # Get the first step to execute
                first_step = transaction_flow_service.get_next_step(cmd.wallet_address)
                if not first_step:
                    return {
                        "success": False,
                        "message": "Failed to prepare transaction steps",
                        "error_details": {
                            "error": "No transaction steps available",
                            "protocols_tried": [quote_result.get("protocol", "unknown")],
                            "suggestion": "Please try again."
                        }
                    }

                # Return the first step with flow information
                return {
                    "success": True,
                    "content": {
                        "type": "multi_step_transaction",
                        "message": f"Step {first_step.step_number} of {len(all_steps)}: {first_step.description}",
                        "transaction": {
                            "to": first_step.to,
                            "data": first_step.data,
                            "value": first_step.value,
                            "gas_limit": first_step.gas_limit,
                            "chainId": cmd.chain_id
                        },
                        "flow_info": {
                            "flow_id": flow.flow_id,
                            "current_step": 1,
                            "total_steps": len(all_steps),
                            "step_type": first_step.step_type.value
                        }
                    },
                    "metadata": {
                        "transaction": {
                            "to": first_step.to,
                            "data": first_step.data,
                            "value": first_step.value,
                            "gas_limit": first_step.gas_limit,
                            "chainId": cmd.chain_id
                        },
                        "protocol": quote_result.get("protocol", "unknown"),
                        "is_multi_step": True,
                        "flow_id": flow.flow_id,
                        "quote": quote_result
                    }
                }
            else:
                # Single-step transaction - use existing logic
                tx_result = await swap_service.build_transaction(
                    quote=quote_result,
                    chain_id=cmd.chain_id,
                    wallet_address=cmd.wallet_address
                )

                # Check for errors in transaction building
                if "error" in tx_result:
                    return {
                        "success": False,
                        "message": tx_result["error"],
                        "error_details": {
                            "error": tx_result["error"],
                            "technical_details": tx_result.get("technical_details", ""),
                            "protocols_tried": [quote_result.get("protocol", "unknown")],
                            "suggestion": "Please try again in a few moments."
                        }
                    }

            # Get token info for display using token service
            to_token_info = await token_service.get_token_info(cmd.chain_id, meta["to_token"])
            protocol_name = quote_result.get("protocol", "unknown")

            # Create token output info
            if to_token_info:
                token_out_info = {
                    "symbol": to_token_info.get("symbol", meta["to_token"].upper()),
                    "address": to_token_info.get("address", ""),
                    "metadata": to_token_info.get("metadata", {"decimals": 18})
                }
            else:
                token_out_info = {
                    "symbol": meta["to_token"].upper(),
                    "address": meta["to_token"] if meta["to_token"].startswith("0x") else "",
                    "metadata": {
                        "decimals": 18
                    }
                }

            # Return success response with transaction data for execution
            return {
                "success": True,
                "content": {
                    "type": "swap_transaction",
                    "message": f"Transaction ready for execution via {protocol_name}",
                    "transaction": tx_result["transaction"],
                    "protocol": protocol_name,
                    "token_out": token_out_info
                },
                "metadata": {
                    "transaction": tx_result["transaction"],
                    "protocol": protocol_name,
                    "token_out": token_out_info,
                    "quote": quote_result
                }
            }

        except Exception as e:
            logger.exception("Error processing swap confirmation")

            # Return structured error response
            return {
                "success": False,
                "message": "Failed to prepare your swap transaction.",
                "error_details": {
                    "error": "Failed to prepare your swap transaction.",
                    "technical_details": str(e),
                    "protocols_tried": [],
                    "suggestion": "This might be a temporary issue. Please try again in a few moments."
                }
            }

    # Support multiple formats:
    # 1. "swap <amount> <tokenIn> to <tokenOut>" - swap 1.5 ETH to USDC
    # 2. "swap <amount> <tokenIn> for <tokenOut>" - swap 1.5 ETH for USDC
    # 3. "swap $<amount> of <tokenIn> to <tokenOut>" - swap $100 of ETH to USDC
    # 4. "swap $<amount> of <tokenIn> for <tokenOut>" - swap $100 of ETH for USDC
    # 5. "swap $<amount> worth of <tokenIn> to <tokenOut>" - swap $100 worth of ETH to USDC

    amount_str = None
    token_in_symbol = None
    token_out_symbol = None
    is_usd_amount = False

    # Try format: "swap $<amount> of <tokenIn> to/for <tokenOut>"
    m = re.match(r"swap\s+\$?([\d\.]+)\s+(?:of|worth\s+of)\s+(\S+)\s+(to|for)\s+(\S+)", cmd.command, re.IGNORECASE)
    if m:
        amount_str, token_in_symbol, _, token_out_symbol = m.groups()
        is_usd_amount = "$" in cmd.command
    else:
        # Try format: "swap <amount> <tokenIn> to/for <tokenOut>"
        m = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+(to|for)\s+(\S+)", cmd.command, re.IGNORECASE)
        if m:
            amount_str, token_in_symbol, _, token_out_symbol = m.groups()
            is_usd_amount = False

    # If still no match, return an error
    if not m:
        return {
            "success": False,
            "message": "Invalid swap command format. Try: 'swap 1.5 ETH to USDC' or 'swap $100 of ETH to USDC'",
            "error_details": {
                "error": "Invalid swap command format. Try: 'swap 1.5 ETH to USDC' or 'swap $100 of ETH to USDC'",
                "suggestion": "Examples: 'swap 1.5 ETH to USDC', 'swap $100 of ETH to USDC', 'swap 0.5 WBTC for DAI'",
                "protocols_tried": []
            }
        }

    try:
        amount = float(amount_str)
    except ValueError:
        return {
            "success": False,
            "message": f"Invalid amount format: {amount_str}",
            "error_details": {
                "error": f"Invalid amount format: {amount_str}",
                "suggestion": "Please provide a valid number for the amount.",
                "protocols_tried": []
            }
        }

    # Get token info using enhanced resolution (registry + token service)
    token_in = await resolve_token_enhanced(cmd.chain_id, token_in_symbol)
    token_out = await resolve_token_enhanced(cmd.chain_id, token_out_symbol)

    # Get chain name for user-friendly messages
    current_chain_name = await token_service.get_chain_name(cmd.chain_id)

    # Check if from_token is available on current chain
    if not token_in:
        return {
            "success": False,
            "message": f"{token_in_symbol.upper()} is not available on {current_chain_name}.",
            "error_details": {
                "error": f"{token_in_symbol.upper()} is not available on {current_chain_name}.",
                "suggestion": f"Try using a different token or check if {token_in_symbol.upper()} exists on {current_chain_name}.",
                "protocols_tried": [],
                "token_availability": {
                    "token": token_in_symbol.upper(),
                    "current_chain": current_chain_name,
                    "available_chains": []
                }
            }
        }

    # Check if to_token is available on current chain
    if not token_out:
        return {
            "success": False,
            "message": f"{token_out_symbol.upper()} is not available on {current_chain_name}.",
            "error_details": {
                "error": f"{token_out_symbol.upper()} is not available on {current_chain_name}.",
                "suggestion": f"Try using a different token or check if {token_out_symbol.upper()} exists on {current_chain_name}.",
                "protocols_tried": [],
                "token_availability": {
                    "token": token_out_symbol.upper(),
                    "current_chain": current_chain_name,
                    "available_chains": []
                }
            }
        }

    # Store for quotes (include chain_id to detect network switches)
    last_swaps[cmd.wallet_address] = {
        "from_token": token_in["address"] or token_in_symbol,
        "to_token": token_out["address"] or token_out_symbol,
        "amount": amount,
        "chain_id": cmd.chain_id
    }

    # Check if we need contract addresses
    requires_contract = not token_in["address"] or not token_out["address"]

    # Get chain name using mapping
    chain_names = {
        1: "Ethereum",
        42161: "Arbitrum One",
        137: "Polygon",
        10: "Optimism",
        56: "BNB Chain",
        43114: "Avalanche",
        8453: "Base",
        534352: "Scroll",
        324: "zkSync Era",
        59144: "Linea",
        5000: "Mantle",
        81457: "Blast"
    }
    chain_name = chain_names.get(cmd.chain_id, f"Chain {cmd.chain_id}")

    return {
        "content": {
            "type": "swap_confirmation",
            "amount": amount,
            "token_in": token_in,
            "token_out": token_out,
            "is_target_amount": False,
            "amount_is_usd": is_usd_amount,
            "note": None,
            "metadata": {
                "requires_contract": requires_contract,
                "token_symbol": token_out_symbol if not token_out["address"] else None,
                "chain_id": cmd.chain_id,
                "chain_name": chain_name,
                "aggregator_info": {
                    "supported_aggregators": ["0x", "brian"],
                    "requires_api_key": {
                        "0x": True,
                        "brian": True
                    }
                } if not requires_contract else None
            }
        }
    }

@router.post("/quotes")
async def get_swap_quotes(req: SwapQuotesRequest) -> Dict[str, Any]:
    """Get swap quotes from multiple protocols."""
    try:
        # Get stored swap metadata
        meta = last_swaps.get(req.wallet_address)
        if not meta:
            raise HTTPException(status_code=400, detail="No pending swap to quote")

        # Get quotes from swap service
        quote_result = await swap_service.get_quote(
            from_token_id=meta["from_token"],
            to_token_id=meta["to_token"],
            amount=Decimal(meta["amount"]),
            chain_id=req.chain_id,
            wallet_address=req.wallet_address
        )

        # Check for errors
        if "error" in quote_result:
            # Prepare detailed error response
            error_response = {
                "error": quote_result["error"],
                "protocols_tried": quote_result.get("protocols_tried", []),
                "suggestion": quote_result.get("suggestion", "Please try a different token pair or amount.")
            }

            if "technical_details" in quote_result:
                error_response["technical_details"] = quote_result["technical_details"]

            if "protocol_errors" in quote_result:
                error_response["protocol_errors"] = quote_result["protocol_errors"]

            # Return a structured error response to the client
            return {
                "success": False,
                "error_details": error_response,
                "message": error_response["error"]
            }

        # Get token info for display using token service
        to_token_info = await token_service.get_token_info(req.chain_id, meta["to_token"])

        # Format the response
        protocol_name = quote_result.get("protocol", "unknown")
        steps = quote_result.get("steps", [])
        metadata = quote_result.get("metadata", {})

        # Create a standardized quote response
        formatted_quote = {
            "protocol": protocol_name,
            "metadata": metadata,
            "steps": steps
        }

        # Create token output info
        if to_token_info:
            token_out_info = {
                "symbol": to_token_info.get("symbol", meta["to_token"].upper()),
                "address": to_token_info.get("address", ""),
                "metadata": to_token_info.get("metadata", {"decimals": 18})
            }
        else:
            token_out_info = {
                "symbol": meta["to_token"].upper(),
                "address": meta["to_token"] if meta["to_token"].startswith("0x") else "",
                "metadata": {
                    "decimals": 18
                }
            }

        # Return in the expected format
        return {
            "success": True,
            "content": {
                "type": "swap_result",
                "message": f"Swap successful via {protocol_name}",
                "quotes": [formatted_quote],
                "token_out": token_out_info
            },
            "metadata": {
                "quotes": [formatted_quote],
                "token_out": token_out_info,
                "protocol": protocol_name
            }
        }

    except Exception as e:
        logger.exception(f"Error getting quotes: {str(e)}")

        # Extract error message
        error_message = str(e)

        # Create user-friendly error message based on common errors
        user_message = "Unable to process swap request."
        suggestion = "This might be a temporary issue. Please try again in a few moments."

        if "not supported" in error_message.lower():
            user_message = "This token pair is not supported on the selected chain."
            suggestion = "Try a different token pair or switch to another blockchain network."
        elif "insufficient liquidity" in error_message.lower():
            user_message = "Insufficient liquidity for this swap."
            suggestion = "Try a smaller amount or a different token pair."
        elif "slippage" in error_message.lower():
            user_message = "Slippage too high for this swap."
            suggestion = "Try a smaller amount or adjust slippage tolerance."
        elif "api key" in error_message.lower():
            user_message = "API key issue with swap provider."
            suggestion = "Please contact support to resolve this issue."
        elif "route" in error_message.lower():
            user_message = "No valid swap route found."
            suggestion = "Try a different token pair or switch to another blockchain network."

        # Return a structured error response
        error_response = {
            "error": user_message,
            "technical_details": error_message,
            "protocols_tried": [],
            "suggestion": suggestion
        }

        return {
            "success": False,
            "error_details": error_response,
            "message": user_message
        }

@router.post("/build-transaction")
async def build_transaction(req: SwapQuotesRequest) -> Dict[str, Any]:
    """Build a transaction from a swap quote."""
    try:
        # Get stored swap metadata
        meta = last_swaps.get(req.wallet_address)
        if not meta:
            raise HTTPException(status_code=400, detail="No pending swap to build transaction for")

        # Get quote first
        quote_result = await swap_service.get_quote(
            from_token_id=meta["from_token"],
            to_token_id=meta["to_token"],
            amount=Decimal(meta["amount"]),
            chain_id=req.chain_id,
            wallet_address=req.wallet_address
        )

        # Check for errors
        if "error" in quote_result:
            raise HTTPException(
                status_code=400,
                detail=quote_result["error"]
            )

        # Build transaction
        tx_result = await swap_service.build_transaction(
            quote=quote_result,
            chain_id=req.chain_id,
            wallet_address=req.wallet_address
        )

        # Check for errors
        if "error" in tx_result:
            raise HTTPException(
                status_code=400,
                detail=tx_result["error"]
            )

        return {
            "transaction": tx_result["transaction"],
            "protocol": quote_result.get("protocol", "unknown")
        }

    except Exception as e:
        logger.exception(f"Error building transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_swap_system() -> Dict[str, Any]:
    """Test endpoint to verify swap system health."""
    try:
        # Test token service with common tokens
        sample_tokens = []
        for token_id in ["eth", "usdc", "wbtc"]:
            token_info = await token_service.get_token_info(1, token_id)  # Test on Ethereum
            if token_info:
                sample_tokens.append({
                    "id": token_id,
                    "symbol": token_info.get("symbol", token_id.upper()),
                    "address": token_info.get("address", ""),
                    "source": token_info.get("metadata", {}).get("source", "unknown")
                })

        # Test swap service
        swap_test = "Swap service available"
        try:
            # This is just a basic availability check
            if hasattr(swap_service, 'get_quote'):
                swap_test = "Swap service operational"
        except Exception:
            swap_test = "Swap service error"

        return {
            "status": "healthy",
            "token_service": {
                "status": "operational",
                "sample_tokens": sample_tokens
            },
            "swap_service": {
                "status": swap_test
            },
            "message": "Swap system is operational with scalable token resolution"
        }
    except Exception as e:
        logger.exception("Error testing swap system")
        return {
            "status": "error",
            "message": f"System error: {str(e)}"
        }

# Multi-step transaction endpoints

class TransactionStepRequest(BaseModel):
    wallet_address: str
    chain_id: int
    tx_hash: str
    success: bool = True
    error: Optional[str] = None

@router.post("/complete-step")
async def complete_transaction_step(req: TransactionStepRequest) -> Dict[str, Any]:
    """Mark a transaction step as completed and get the next step."""
    try:
        # Complete the current step
        success = transaction_flow_service.complete_step(
            wallet_address=req.wallet_address,
            tx_hash=req.tx_hash,
            success=req.success,
            error=req.error
        )

        if not success:
            return {
                "success": False,
                "message": "No active transaction flow found",
                "error": "No active transaction flow"
            }

        # Get the next step if available
        next_step = transaction_flow_service.get_next_step(req.wallet_address)
        flow_status = transaction_flow_service.get_flow_status(req.wallet_address)

        if next_step:
            # Return next step to execute
            return {
                "success": True,
                "has_next_step": True,
                "content": {
                    "type": "multi_step_transaction",
                    "message": f"Step {next_step.step_number} of {flow_status['total_steps']}: {next_step.description}",
                    "transaction": {
                        "to": next_step.to,
                        "data": next_step.data,
                        "value": next_step.value,
                        "gas_limit": next_step.gas_limit,
                        "chainId": req.chain_id
                    },
                    "flow_info": {
                        "flow_id": flow_status["flow_id"],
                        "current_step": next_step.step_number,
                        "total_steps": flow_status["total_steps"],
                        "step_type": next_step.step_type.value
                    }
                },
                "metadata": {
                    "transaction": {
                        "to": next_step.to,
                        "data": next_step.data,
                        "value": next_step.value,
                        "gas_limit": next_step.gas_limit,
                        "chainId": req.chain_id
                    },
                    "is_multi_step": True,
                    "flow_id": flow_status["flow_id"]
                }
            }
        else:
            # Transaction flow is complete
            return {
                "success": True,
                "has_next_step": False,
                "content": {
                    "type": "transaction_complete",
                    "message": "🎉 Swap completed successfully! All transaction steps have been executed.",
                    "flow_status": flow_status
                },
                "metadata": {
                    "is_complete": True,
                    "flow_status": flow_status
                }
            }

    except Exception as e:
        logger.exception(f"Error completing transaction step: {str(e)}")
        return {
            "success": False,
            "message": f"Error processing transaction step: {str(e)}",
            "error": str(e)
        }

@router.get("/flow-status/{wallet_address}")
async def get_transaction_flow_status(wallet_address: str) -> Dict[str, Any]:
    """Get the current status of a user's transaction flow."""
    try:
        flow_status = transaction_flow_service.get_flow_status(wallet_address)

        if not flow_status:
            return {
                "success": False,
                "message": "No active transaction flow found",
                "has_active_flow": False
            }

        return {
            "success": True,
            "has_active_flow": True,
            "flow_status": flow_status
        }

    except Exception as e:
        logger.exception(f"Error getting flow status: {str(e)}")
        return {
            "success": False,
            "message": f"Error getting flow status: {str(e)}",
            "error": str(e)
        }

@router.post("/cancel-flow")
async def cancel_transaction_flow(req: SwapQuotesRequest) -> Dict[str, Any]:
    """Cancel the current transaction flow for a user."""
    try:
        success = transaction_flow_service.cancel_flow(req.wallet_address)

        if success:
            return {
                "success": True,
                "message": "Transaction flow cancelled successfully"
            }
        else:
            return {
                "success": False,
                "message": "No active transaction flow to cancel"
            }

    except Exception as e:
        logger.exception(f"Error cancelling flow: {str(e)}")
        return {
            "success": False,
            "message": f"Error cancelling flow: {str(e)}",
            "error": str(e)
        }
