"""
Swap aggregator endpoints using 0x API with Permit2.
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from decimal import Decimal
from app.services.swap_service import fetch_swap_quote, build_swap_transaction
from app.services.brian.client import brian_client

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

class QuoteResponseItem(BaseModel):
    aggregator: str
    protocol: str
    buy_amount: str
    minimum_received: str
    gas: Optional[str]
    gas_usd: Optional[str]
    to: str
    data: str
    value: str
    permit2: Optional[Dict[str, Any]]  # Added for Permit2 support
    zid: Optional[str]  # Added for transaction tracking

class SwapExecuteRequest(BaseModel):
    wallet_address: str
    chain_id: int
    selected_quote: QuoteResponseItem

# 1. Parse and confirm swap command
@router.post("/process-command")
async def process_swap_command(cmd: SwapCommand) -> Dict[str, Any]:
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

    amount, token_in, token_out = m.groups()

    # Store for quotes
    last_swaps[cmd.wallet_address] = {
        "from_token": token_in,
        "to_token": token_out,
        "amount": amount
    }

    message = f"Confirm swap: {amount} {token_in} → {token_out}?"
    return {"content": {"type": "swap_confirmation", "message": message}, "metadata": last_swaps[cmd.wallet_address]}

# 2. Fetch quotes
@router.post("/get-quotes")
async def get_swap_quotes(req: SwapQuotesRequest) -> Dict[str, Any]:
    meta = last_swaps.get(req.wallet_address)
    if not meta:
        raise HTTPException(status_code=400, detail="No swap command found for this wallet")
    from_token = meta["from_token"]
    to_token = meta["to_token"]
    amt = Decimal(meta["amount"])

    # Check if this is Scroll chain (chain ID 534352)
    is_scroll_chain = req.chain_id == 534352

    # For Scroll chain, use Brian API
    if is_scroll_chain:
        try:
            # Return a response indicating this is a Brian operation
            return {
                "is_brian_operation": True,
                "token_out": {"symbol": to_token, "decimals": 18},
                "message": "Using Brian API for Scroll chain swaps"
            }
        except Exception as e:
            # If Brian API fails, fall back to 0x API
            print(f"Brian API failed, falling back to 0x API: {str(e)}")
            is_scroll_chain = False

    # For other chains or if Brian API failed, use 0x API
    if not is_scroll_chain:
        try:
            data = await fetch_swap_quote(
                from_token=from_token,
                to_token=to_token,
                amount=amt,
                chain_id=req.chain_id,
                taker_address=req.wallet_address
            )

            quote = QuoteResponseItem(
                aggregator="0x",
                protocol="0x",
                buy_amount=data.get("buyAmount", "0"),
                minimum_received=data.get("minBuyAmount", "0"),
                gas=str(data.get("gas", "")),
                gas_usd="",  # Could calculate this if needed
                to=data.get("to", ""),
                data=data.get("data", ""),
                value=data.get("value", "0"),
                permit2=data.get("permit2"),
                zid=data.get("zid")
            )
            return {
                "quotes": [quote.model_dump()],
                "token_out": {"symbol": to_token, "decimals": 18},  # Default decimals, could fetch from token contract
                "is_brian_operation": False
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching quote: {e}") from e

# 3. Build swap transaction
@router.post("/execute")
async def execute_swap(req: SwapExecuteRequest) -> Dict[str, Any]:
    q = req.selected_quote
    return await build_swap_transaction(q.model_dump(), req.chain_id)
