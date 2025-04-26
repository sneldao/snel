"""
Brian API client service.
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class BrianClient:
    """Client for interacting with the Brian API."""

    def __init__(self):
        """Initialize the Brian API client."""
        self.api_key = os.getenv("BRIAN_API_KEY")
        self.api_url = os.getenv("BRIAN_API_URL", "https://api.brianknows.org/api/v0")
        self.verify_ssl = os.getenv("DISABLE_SSL_VERIFY", "").lower() not in ("true", "1", "yes")
        self.http_client = None

        if not self.api_key:
            logger.warning("BRIAN_API_KEY environment variable not set")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.http_client

    async def close(self):
        """Close the HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    async def get_quote(self, from_token: str, to_token: str, amount: Decimal,
                       from_chain_id: int, to_chain_id: int) -> Dict[str, Any]:
        """Get a quote for bridging tokens."""
        client = await self._get_client()
        response = await client.get(
            f"{self.api_url}/quote",
            params={
                "fromToken": from_token,
                "toToken": to_token,
                "amount": str(amount),
                "fromChainId": from_chain_id,
                "toChainId": to_chain_id
            }
        )
        response.raise_for_status()
        return response.json()

    async def execute_bridge(self, quote_id: str, wallet_address: str) -> Dict[str, Any]:
        """Execute a bridge transaction."""
        client = await self._get_client()
        response = await client.post(
            f"{self.api_url}/bridge",
            json={
                "quoteId": quote_id,
                "walletAddress": wallet_address
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_balance(self, wallet_address: str, chain_id: int,
                         token_address: Optional[str] = None) -> Dict[str, Any]:
        """Get token balance for a wallet."""
        client = await self._get_client()
        params = {
            "walletAddress": wallet_address,
            "chainId": chain_id
        }
        if token_address:
            params["tokenAddress"] = token_address

        response = await client.get(
            f"{self.api_url}/balance",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_transaction_status(self, tx_hash: str, chain_id: int) -> Dict[str, Any]:
        """Get the status of a transaction."""
        client = await self._get_client()
        response = await client.get(
            f"{self.api_url}/transaction/{tx_hash}",
            params={"chainId": chain_id}
        )
        response.raise_for_status()
        return response.json()

    async def get_swap_transaction(self, from_token: str, to_token: str, amount: Decimal,
                                  chain_id: int, wallet_address: str) -> Dict[str, Any]:
        """Get a swap transaction from the Brian API."""
        client = await self._get_client()
        response = await client.post(
            f"{self.api_url}/swap",
            json={
                "fromToken": from_token,
                "toToken": to_token,
                "amount": str(amount),
                "chainId": chain_id,
                "walletAddress": wallet_address
            }
        )
        response.raise_for_status()
        return response.json()

# Create a singleton instance
brian_client = BrianClient()
