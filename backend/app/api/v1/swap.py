"""
Swap aggregator endpoints using the protocol registry architecture.
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from decimal import Decimal
from app.services.swap_service import swap_service
from app.protocols.registry import protocol_registry
from app.models.token import token_registry, TokenInfo
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/swap", tags=["swap"])

# In-memory store for last swap per wallet
last_swaps: Dict[str, Dict[str, Any]] = {}

# Request/Response models
class SwapCommand(BaseModel):
    command: str
    wallet_address: str
    chain_id: int

class SwapQuotesRequest(BaseModel):
    wallet_address: str
    chain_id: int

class SwapQuoteResponse(BaseModel):
    protocol: str
    rate: float
    gas_cost_usd: Optional[float] = None
    from_amount_usd: Optional[float] = None
    to_amount_usd: Optional[float] = None
    gas_limit: Optional[str] = None
    gas_price: Optional[str] = None
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}

# Helper function to convert TokenInfo to API response format
def token_info_to_api(token: TokenInfo, chain_id: int) -> Dict[str, Any]:
    """Convert TokenInfo to API response format."""
    return {
        "address": token.get_address(chain_id) or "",
        "symbol": token.symbol,
        "name": token.name,
        "metadata": {
            "verified": token.verified,
            "source": token.type,
            "decimals": token.decimals
        }
    }

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
        
        # Get quotes for the confirmed swap
        try:
            quotes = await get_swap_quotes(SwapQuotesRequest(
                wallet_address=cmd.wallet_address,
                chain_id=cmd.chain_id
            ))
            
            # Pass through the response - it already handles errors in the new format
            return quotes
            
        except Exception as e:
            logger.exception("Error getting swap quotes")
            
            # Return structured error response
            return {
                "success": False,
                "message": "Failed to get quotes for your swap request.",
                "error_details": {
                    "error": "Failed to get quotes for your swap request.",
                    "technical_details": str(e),
                    "protocols_tried": [],
                    "suggestion": "This might be a temporary issue. Please try again in a few moments."
                }
            }

    # Support multiple formats:
    # 1. "swap <amount> <tokenIn> to <tokenOut>"
    # 2. "swap <amount> <tokenIn> for <tokenOut>"

    # Try the "to" format first
    m = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+to\s+(\S+)", cmd.command, re.IGNORECASE)

    # If that doesn't match, try the "for" format
    if not m:
        m = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+for\s+(\S+)", cmd.command, re.IGNORECASE)

    # If still no match, return an error
    if not m:
        return {
            "success": False,
            "message": "Invalid swap command format. Use: 'swap <amount> <tokenIn> to <tokenOut>'",
            "error_details": {
                "error": "Invalid swap command format. Use: 'swap <amount> <tokenIn> to <tokenOut>'",
                "suggestion": "Try formatting your command as: swap 1.5 ETH to USDC",
                "protocols_tried": []
            }
        }

    amount_str, token_in_symbol, token_out_symbol = m.groups()
    
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

    # Get token info using our new token registry
    from_token = await protocol_registry.resolve_token(cmd.chain_id, token_in_symbol)
    to_token = await protocol_registry.resolve_token(cmd.chain_id, token_out_symbol)

    # Convert to API format or create placeholder
    if from_token:
        token_in = token_info_to_api(from_token, cmd.chain_id)
    else:
        token_in = {
            "address": "",
            "symbol": token_in_symbol.upper(),
            "name": token_in_symbol.upper(),
            "metadata": {
                "verified": False,
                "source": "user_input",
                "decimals": 18
            }
        }

    if to_token:
        token_out = token_info_to_api(to_token, cmd.chain_id)
    else:
        token_out = {
            "address": "",
            "symbol": token_out_symbol.upper(),
            "name": token_out_symbol.upper(),
            "metadata": {
                "verified": False,
                "source": "user_input",
                "decimals": 18
            }
        }

    # Store for quotes
    last_swaps[cmd.wallet_address] = {
        "from_token": token_in["address"] or token_in_symbol,
        "to_token": token_out["address"] or token_out_symbol,
        "amount": amount
    }

    # Check if we need contract addresses
    requires_contract = not token_in["address"] or not token_out["address"]
    unverified_token = not token_in["metadata"]["verified"] or not token_out["metadata"]["verified"]

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
            "amount_is_usd": False,
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
            
        # Get token info for display
        to_token = await protocol_registry.resolve_token(req.chain_id, meta["to_token"])
        
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
        token_out_info = {}
        if to_token:
            token_out_info = token_info_to_api(to_token, req.chain_id)
        else:
            token_out_info = {
                "symbol": meta["to_token"],
                "address": meta["to_token"] if meta["to_token"].startswith("0x") else "",
                "metadata": {
                    "decimals": 18
                }
            }
        
        # Return in the expected format
        return {
            "success": True,
            "quotes": [formatted_quote],
            "token_out": token_out_info,
            "protocol": protocol_name
        }
        
    except Exception as e:
        logger.exception(f"Error getting quotes: {str(e)}")
        
        # Return a structured error response for unexpected errors
        error_response = {
            "error": "Unable to process swap request. Please try again.",
            "technical_details": str(e),
            "protocols_tried": [],
            "suggestion": "This might be a temporary issue. Please try again in a few moments."
        }
        
        return {
            "success": False,
            "error_details": error_response,
            "message": error_response["error"]
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
        # Check if protocol registry is initialized
        protocols = []
        for protocol_id, protocol in protocol_registry.protocols.items():
            protocols.append({
                "id": protocol_id,
                "name": protocol.name if hasattr(protocol, "name") else protocol_id,
                "supported_chains": protocol.supported_chains if hasattr(protocol, "supported_chains") else []
            })
            
        # Check token registry
        sample_tokens = []
        for token_id in ["eth", "usdc", "weth"]:
            token = token_registry.get_token(token_id)
            if token:
                sample_tokens.append({
                    "id": token.id,
                    "symbol": token.symbol,
                    "chains": list(token.addresses.keys())
                })
                
        return {
            "status": "healthy",
            "protocols": protocols,
            "tokens": sample_tokens,
            "message": "Swap system is operational"
        }
    except Exception as e:
        logger.exception("Error testing swap system")
        return {
            "status": "error",
            "message": f"System error: {str(e)}"
        }
