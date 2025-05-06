from decimal import Decimal
from typing import Dict, Any
import os
import httpx

# Get the 0x API URL and API key from environment variables
ZEROEX_API_URL = os.getenv("ZEROEX_API_URL", "https://api.0x.org")
ZEROEX_API_KEY = os.getenv("ZEROEX_API_KEY", "")  # Correct environment variable name for 0x API key

async def fetch_swap_quote(from_token: str, to_token: str, amount: Decimal, chain_id: int, decimals: int = 18) -> Dict[str, Any]:
    """Fetches a swap quote from the 0x API."""
    sell_amount = int(amount * (Decimal(10) ** decimals))

    # Prepare headers with API key if available
    headers = {}
    if ZEROEX_API_KEY:
        headers["0x-api-key"] = ZEROEX_API_KEY

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{ZEROEX_API_URL}/swap/v1/quote",
                params={
                    "sellToken": from_token,
                    "buyToken": to_token,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id
                },
                headers=headers
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"Error fetching swap quote: {str(e)}")
        raise

async def build_swap_transaction(quote: Dict[str, Any], chain_id: int) -> Dict[str, Any]:
    return {
        "to": quote.get("to", ""),
        "data": quote.get("data", ""),
        "value": quote.get("value", "0"),
        "gas_limit": str(quote.get("gas", "")),
        "chainId": chain_id
    }