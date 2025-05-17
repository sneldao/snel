"""
0x Protocol implementation.
"""
import os
import httpx
from decimal import Decimal
from typing import Dict, Any, Optional
from .base import SwapProtocol
from ..config.chains import is_protocol_supported

class ZeroXProtocol(SwapProtocol):
    """0x Protocol implementation."""

    def __init__(self):
        """Initialize the 0x protocol."""
        self.api_url = os.getenv("ZEROEX_API_URL", "https://api.0x.org")
        self.api_key = os.getenv("ZEROX_API_KEY", "")
        if not self.api_key:
            raise ValueError("ZEROX_API_KEY environment variable not set")

    @property
    def name(self) -> str:
        return "0x"

    def is_supported(self, chain_id: int) -> bool:
        return is_protocol_supported(chain_id, "0x")

    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Get a quote from 0x API."""
        if not self.is_supported(chain_id):
            raise ValueError(f"Chain {chain_id} not supported by 0x protocol")

        headers = {
            "0x-api-key": self.api_key,
            "0x-version": "v2"
        }

        # First get token info to get decimals
        from_token_info = await self.get_token_info(from_token, chain_id)
        if not from_token_info:
            raise ValueError(f"Token {from_token} not found on chain {chain_id}")

        sell_amount = int(amount * (Decimal(10) ** from_token_info["decimals"]))

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get price quote first
            price_resp = await client.get(
                f"{self.api_url}/swap/permit2/price",
                params={
                    "sellToken": from_token,
                    "buyToken": to_token,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": wallet_address
                },
                headers=headers
            )
            price_resp.raise_for_status()
            price_data = price_resp.json()

            # If price looks good, get firm quote
            quote_resp = await client.get(
                f"{self.api_url}/swap/permit2/quote",
                params={
                    "sellToken": from_token,
                    "buyToken": to_token,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": wallet_address,
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

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Build a transaction from a 0x quote."""
        return {
            "to": quote.get("to", ""),
            "data": quote.get("data", ""),
            "value": quote.get("value", "0"),
            "gas_limit": quote.get("gas", "500000"),  # Default gas limit if not provided
            "chainId": chain_id,
            "permit2": quote.get("permit2"),
            "zid": quote.get("zid")
        }

    async def get_token_info(
        self,
        token_address: str,
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token information from 0x API."""
        if not self.is_supported(chain_id):
            return None

        headers = {
            "0x-api-key": self.api_key,
            "0x-version": "v2"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/swap/tokens",
                    params={"chainId": chain_id},
                    headers=headers
                )
                response.raise_for_status()
                tokens = response.json()
                
                # Find the token in the list
                for token in tokens:
                    if token.get("address", "").lower() == token_address.lower():
                        return {
                            "address": token["address"],
                            "symbol": token["symbol"],
                            "name": token["name"],
                            "decimals": token["decimals"]
                        }
                return None
        except Exception:
            return None 