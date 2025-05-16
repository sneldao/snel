"""
Swap service using 0x API with Permit2.
"""
from decimal import Decimal
from typing import Dict, Any
import os
import httpx

# Get the 0x API URL and API key from environment variables
ZEROEX_API_URL = os.getenv("ZEROEX_API_URL", "https://api.0x.org")
ZEROX_API_KEY = os.getenv("ZEROX_API_KEY", "")  # Updated environment variable name

async def fetch_swap_quote(from_token: str, to_token: str, amount: Decimal, chain_id: int, taker_address: str, decimals: int = 18) -> Dict[str, Any]:
    """Fetches a swap quote from the 0x API using Permit2."""
    sell_amount = int(amount * (Decimal(10) ** decimals))

    # Prepare headers with API key and version
    headers = {
        "0x-api-key": ZEROX_API_KEY,
        "0x-version": "v2"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First get a price quote
            price_resp = await client.get(
                f"{ZEROEX_API_URL}/swap/permit2/price",
                params={
                    "sellToken": from_token,
                    "buyToken": to_token,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": taker_address
                },
                headers=headers
            )
            price_resp.raise_for_status()
            price_data = price_resp.json()

            # If price looks good, get the firm quote
            quote_resp = await client.get(
                f"{ZEROEX_API_URL}/swap/permit2/quote",
                params={
                    "sellToken": from_token,
                    "buyToken": to_token,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": taker_address,
                    "slippageBps": "100"  # Default 1% slippage
                },
                headers=headers
            )
            quote_resp.raise_for_status()
            quote_data = quote_resp.json()

            return {
                "buyAmount": quote_data.get("buyAmount"),
                "minBuyAmount": quote_data.get("minBuyAmount"),
                "price": float(quote_data.get("buyAmount", 0)) / float(sell_amount) if sell_amount else 0,
                "gas": quote_data.get("gas"),
                "gasPrice": quote_data.get("gasPrice"),
                "permit2": quote_data.get("permit2"),
                "to": quote_data.get("transaction", {}).get("to"),
                "data": quote_data.get("transaction", {}).get("data"),
                "value": quote_data.get("transaction", {}).get("value", "0"),
                "chainId": chain_id,
                "zid": quote_data.get("zid")
            }
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"Error fetching swap quote: {str(e)}")
        raise

async def build_swap_transaction(quote: Dict[str, Any], chain_id: int) -> Dict[str, Any]:
    """Builds a swap transaction from a quote."""
    return {
        "to": quote.get("to", ""),
        "data": quote.get("data", ""),
        "value": quote.get("value", "0"),
        "gas_limit": quote.get("gas", "500000"),  # Default gas limit if not provided
        "chainId": chain_id,
        "permit2": quote.get("permit2"),  # Include Permit2 data for frontend
        "zid": quote.get("zid")  # Include ZID for tracking
    }