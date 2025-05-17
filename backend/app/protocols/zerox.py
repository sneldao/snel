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

        # Map chain_id to the correct 0x API URL
        base_url = self._get_api_url_for_chain(chain_id)

        headers = {
            "0x-api-key": self.api_key,
            "0x-version": "v2"
        }

        # First get token info to get decimals
        from_token_info = await self.get_token_info(from_token, chain_id)
        if not from_token_info:
            # Use default decimals based on common tokens
            if from_token.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                # ETH
                from_token_decimals = 18
            elif from_token.lower() == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913" and chain_id == 8453:
                # USDC on Base
                from_token_decimals = 6
            else:
                # Default to 18
                from_token_decimals = 18
        else:
            from_token_decimals = from_token_info["decimals"]

        sell_amount = int(amount * (Decimal(10) ** from_token_decimals))

        # Special handling for native ETH
        if from_token.lower() == "eth" or from_token.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            from_token = "ETH"
        if to_token.lower() == "eth" or to_token.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            to_token = "ETH"

        print(f"Getting 0x quote on chain {chain_id} for {from_token} -> {to_token}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get price quote first
            try:
                price_resp = await client.get(
                    f"{base_url}/swap/permit2/price",
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
                    f"{base_url}/swap/permit2/quote",
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
            except httpx.HTTPStatusError as e:
                print(f"0x API HTTP error: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"0x API error: {e.response.text}")
            except Exception as e:
                print(f"0x API error: {str(e)}")
                raise

    def _get_api_url_for_chain(self, chain_id: int) -> str:
        """Get the correct 0x API URL based on chain ID."""
        # Most chains use the main API
        base_urls = {
            1: "https://api.0x.org",  # Ethereum
            137: "https://polygon.api.0x.org",  # Polygon 
            56: "https://bsc.api.0x.org",  # BSC
            42161: "https://arbitrum.api.0x.org",  # Arbitrum
            10: "https://optimism.api.0x.org",  # Optimism
            43114: "https://avalanche.api.0x.org",  # Avalanche
            59144: "https://linea.api.0x.org",  # Linea
            8453: "https://base.api.0x.org",  # Base
            5000: "https://mantle.api.0x.org",  # Mantle
            81457: "https://blast.api.0x.org",  # Blast
        }
        return base_urls.get(chain_id, self.api_url)

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