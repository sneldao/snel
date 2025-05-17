"""
Swap aggregator endpoints using the protocol manager architecture.
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from decimal import Decimal
from app.services.swap_service import swap_service
from app.services.token_service import token_service

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
    protocol_name: Optional[str] = None

class QuoteResponseItem(BaseModel):
    protocol: str
    buy_amount: str
    minimum_received: str
    gas: Optional[str]
    gas_usd: Optional[str]
    to: str
    data: str
    value: str
    permit2: Optional[Dict[str, Any]] = None  # For EVM chains
    zid: Optional[str] = None  # For transaction tracking
    calldata: Optional[List[str]] = None  # For Starknet
    entrypoint: Optional[str] = None  # For Starknet
    contract_address: Optional[str] = None  # For Starknet

class SwapExecuteRequest(BaseModel):
    wallet_address: str
    chain_id: int
    selected_quote: QuoteResponseItem

# 1. Parse and confirm swap command
@router.post("/process-command")
async def process_swap_command(cmd: SwapCommand) -> Dict[str, Any]:
    # Check if this is a confirmation
    if cmd.command.lower().strip() == "yes":
        meta = last_swaps.get(cmd.wallet_address)
        if not meta:
            raise HTTPException(status_code=400, detail="No pending swap to confirm")
        
        # Get quotes for the confirmed swap
        try:
            quotes = await get_swap_quotes(SwapQuotesRequest(
                wallet_address=cmd.wallet_address,
                chain_id=cmd.chain_id
            ))
            return {
                "content": {
                    "type": "swap_quotes",
                    "quotes": quotes["quotes"],
                    "token_out": quotes["token_out"],
                    "protocol": quotes["protocol"]
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(
            status_code=400,
            detail="Invalid swap command format. Use: 'swap <amount> <tokenIn> to <tokenOut>' or 'swap <amount> <tokenIn> for <tokenOut>'"
        )

    amount_str, token_in_symbol, token_out_symbol = m.groups()
    
    try:
        amount = float(amount_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid amount format: {amount_str}"
        )

    # Get token info using the token service
    token_in = await token_service.get_token_info(cmd.chain_id, token_in_symbol)
    token_out = await token_service.get_token_info(cmd.chain_id, token_out_symbol)

    # If tokens not found, create placeholder info
    if not token_in:
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

    if not token_out:
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

    # Get chain name from token service
    chain_name = await token_service.get_chain_name(cmd.chain_id)

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

# 2. Fetch quotes
@router.post("/get-quotes")
async def get_swap_quotes(req: SwapQuotesRequest) -> Dict[str, Any]:
    meta = last_swaps.get(req.wallet_address)
    if not meta:
        raise HTTPException(status_code=400, detail="No swap command found for this wallet")

    try:
        # Get quote using the swap service
        quote = await swap_service.get_quote(
            from_token=meta["from_token"],
            to_token=meta["to_token"],
            amount=Decimal(meta["amount"]),
            chain_id=req.chain_id,
            wallet_address=req.wallet_address,
            protocol_name=req.protocol_name
        )

        # Get token info for the output token
        token_info = await swap_service.get_token_info(
            token_address=meta["to_token"],
            chain_id=req.chain_id,
            protocol_name=quote.get("protocol")
        )

        # Format response
        quote_item = QuoteResponseItem(
            protocol=quote["protocol"],
            buy_amount=quote.get("buyAmount", "0"),
            minimum_received=quote.get("minBuyAmount", "0"),
            gas=str(quote.get("gas", "")),
            gas_usd="",  # Could calculate this if needed
            to=quote.get("to", ""),
            data=quote.get("data", ""),
            value=quote.get("value", "0"),
            permit2=quote.get("permit2"),
            zid=quote.get("zid"),
            calldata=quote.get("calldata"),
            entrypoint=quote.get("entrypoint"),
            contract_address=quote.get("contractAddress")
        )

        return {
            "quotes": [quote_item.model_dump()],
            "token_out": token_info or {"symbol": meta["to_token"], "decimals": 18},
            "protocol": quote["protocol"]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quote: {str(e)}")

# 3. Build swap transaction
@router.post("/execute")
async def execute_swap(req: SwapExecuteRequest) -> Dict[str, Any]:
    try:
        return await swap_service.build_transaction(
            quote=req.selected_quote.model_dump(),
            chain_id=req.chain_id,
            wallet_address=req.wallet_address
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building transaction: {str(e)}")
