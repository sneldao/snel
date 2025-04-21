"""
Swap aggregator endpoints using 0x API.
"""
import os
import re
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from decimal import Decimal

router = APIRouter(prefix="/swap", tags=["swap"])

# In-memory store for last swap per wallet
last_swaps: Dict[str, Dict[str, Any]] = {}

ZEROEX_API_URL = os.getenv("ZEROEX_API_URL", "https://api.0x.org")
http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    global http_client
    if http_client is None or http_client.is_closed:
        http_client = httpx.AsyncClient(timeout=30.0)
    return http_client

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

class SwapExecuteRequest(BaseModel):
    wallet_address: str
    chain_id: int
    selected_quote: QuoteResponseItem

# 1. Parse and confirm swap command
@router.post("/process-command")
async def process_swap_command(cmd: SwapCommand) -> Dict[str, Any]:
    # Expect: "swap <amount> <tokenIn> to <tokenOut>"
    m = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+to\s+(\S+)", cmd.command, re.IGNORECASE)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid swap command format. Use: swap <amount> <tokenIn> to <tokenOut>")
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
    decimals = 18
    sell_amount = int(amt * (Decimal(10) ** decimals))
    client = await get_http_client()
    try:
        resp = await client.get(
            f"{ZEROEX_API_URL}/swap/v1/quote",
            params={
                "sellToken": from_token,
                "buyToken": to_token,
                "sellAmount": str(sell_amount),
                "chainId": req.chain_id
            }
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quote: {e}")
    quote = QuoteResponseItem(
        aggregator="0x",
        protocol="0x",
        buy_amount=data.get("buyAmount", "0"),
        minimum_received=data.get("buyAmount", "0"),
        gas=str(data.get("gas", "")),
        gas_usd="",
        to=data.get("to", ""),
        data=data.get("data", ""),
        value=data.get("value", "0")
    )
    return {"quotes": [quote.dict()], "token_out": {"symbol": to_token, "decimals": decimals}, "is_brian_operation": False}

# 3. Build swap transaction
@router.post("/execute")
async def execute_swap(req: SwapExecuteRequest) -> Dict[str, Any]:
    q = req.selected_quote
    return {"to": q.to, "data": q.data, "value": q.value, "gas_limit": q.gas, "chainId": req.chain_id}
