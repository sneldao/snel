"""
Brian Protocol implementation.
"""
import os
import httpx
import logging
from decimal import Decimal
from typing import Dict, Any, Optional
from .base import SwapProtocol
from ..config.chains import is_protocol_supported, ChainType, get_chain_info

logger = logging.getLogger(__name__)

class BrianProtocol(SwapProtocol):
    """Brian Protocol implementation."""

    def __init__(self):
        """Initialize the Brian protocol."""
        self.api_key = os.getenv("BRIAN_API_KEY")
        self.api_url = os.getenv("BRIAN_API_URL", "https://api.brianknows.org/api/v0")
        self.verify_ssl = os.getenv("DISABLE_SSL_VERIFY", "").lower() not in ("true", "1", "yes")
        self.http_client = None

        if not self.api_key:
            raise ValueError("BRIAN_API_KEY environment variable not set")

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

    @property
    def name(self) -> str:
        return "brian"

    def is_supported(self, chain_id: int) -> bool:
        return is_protocol_supported(chain_id, "brian")

    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Get a quote from Brian API."""
        if not self.is_supported(chain_id):
            raise ValueError(f"Chain {chain_id} not supported by Brian protocol")

        chain_info = get_chain_info(chain_id)
        if not chain_info:
            raise ValueError(f"Chain {chain_id} not found")

        client = await self._get_client()

        # Handle different chain types
        if chain_info.type == ChainType.STARKNET:
            response = await client.post(
                f"{self.api_url}/starknet/swap",
                json={
                    "fromToken": from_token,
                    "toToken": to_token,
                    "amount": str(amount),
                    "walletAddress": wallet_address
                }
            )
        else:  # EVM chains
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
        data = response.json()

        # Format response based on chain type
        if chain_info.type == ChainType.STARKNET:
            return {
                "buyAmount": data.get("buyAmount"),
                "minBuyAmount": data.get("minBuyAmount"),
                "price": data.get("price"),
                "fee": data.get("fee"),
                "calldata": data.get("calldata"),
                "entrypoint": data.get("entrypoint"),
                "contractAddress": data.get("contractAddress"),
                "chainId": chain_id
            }
        else:
            return {
                "buyAmount": data.get("buyAmount"),
                "minBuyAmount": data.get("minBuyAmount"),
                "price": data.get("price"),
                "gas": data.get("gas"),
                "to": data.get("to"),
                "data": data.get("data"),
                "value": data.get("value", "0"),
                "chainId": chain_id
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Build a transaction from a Brian quote."""
        chain_info = get_chain_info(chain_id)
        if not chain_info:
            raise ValueError(f"Chain {chain_id} not found")

        if chain_info.type == ChainType.STARKNET:
            return {
                "contractAddress": quote.get("contractAddress"),
                "entrypoint": quote.get("entrypoint"),
                "calldata": quote.get("calldata"),
                "chainId": chain_id
            }
        else:  # EVM chains
            return {
                "to": quote.get("to", ""),
                "data": quote.get("data", ""),
                "value": quote.get("value", "0"),
                "gas_limit": quote.get("gas", "500000"),
                "chainId": chain_id
            }

    async def get_token_info(
        self,
        token_address: str,
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token information from Brian API."""
        if not self.is_supported(chain_id):
            return None

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.api_url}/token",
                params={
                    "address": token_address,
                    "chainId": chain_id
                }
            )
            response.raise_for_status()
            token = response.json()
            
            return {
                "address": token["address"],
                "symbol": token["symbol"],
                "name": token["name"],
                "decimals": token["decimals"]
            }
        except Exception:
            return None

    # Additional utility methods from the client
    async def get_balance(
        self,
        wallet_address: str,
        chain_id: int,
        token_address: Optional[str] = None
    ) -> Dict[str, Any]:
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

    async def get_transaction_status(
        self,
        tx_hash: str,
        chain_id: int
    ) -> Dict[str, Any]:
        """Get the status of a transaction."""
        client = await self._get_client()
        response = await client.get(
            f"{self.api_url}/transaction/{tx_hash}",
            params={"chainId": chain_id}
        )
        response.raise_for_status()
        return response.json() 