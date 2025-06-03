"""
0x Protocol adapter implementation.
"""
import os
import httpx
from decimal import Decimal
from typing import Dict, Any, List
from app.models.token import TokenInfo, TokenType


class ZeroXAdapter:
    """0x Protocol adapter."""
    
    # Chain-specific base URLs
    BASE_URLS = {
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

    def __init__(self):
        """Initialize the 0x protocol adapter."""
        self.api_key = os.getenv("ZEROX_API_KEY", "")
        if not self.api_key:
            raise ValueError("ZEROX_API_KEY environment variable not set")
        
        self.http_client = None

    @property
    def protocol_id(self) -> str:
        return "0x"
    
    @property
    def name(self) -> str:
        return "0x Protocol"
    
    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return list(self.BASE_URLS.keys())
    
    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        return chain_id in self.supported_chains
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "0x-api-key": self.api_key,
                    "0x-version": "v2"
                }
            )
        return self.http_client
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
    
    def get_api_url(self, chain_id: int) -> str:
        """Get chain-specific API URL."""
        return self.BASE_URLS.get(chain_id, self.BASE_URLS[1])  # Default to Ethereum
    
    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Get swap quote from 0x API."""
        if not self.is_supported(chain_id):
            raise ValueError(f"Chain {chain_id} not supported by 0x protocol")
        
        # Get token addresses for this chain
        from_address = from_token.get_address(chain_id)
        to_address = to_token.get_address(chain_id)
        
        if not from_address or not to_address:
            raise ValueError(f"One or both tokens not supported on chain {chain_id}")
        
        # Convert to sell amount with proper decimals
        sell_amount = int(amount * (Decimal(10) ** from_token.decimals))
        
        # Convert token addresses to 0x API format
        from_token_param = "ETH" if from_token.type == TokenType.NATIVE else from_address
        to_token_param = "ETH" if to_token.type == TokenType.NATIVE else to_address
        
        # Get API URL for this chain
        api_url = self.get_api_url(chain_id)
        client = await self._get_client()
        
        try:
            # Get price quote first
            price_resp = await client.get(
                f"{api_url}/swap/permit2/price",
                params={
                    "sellToken": from_token_param,
                    "buyToken": to_token_param,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": wallet_address
                }
            )
            price_resp.raise_for_status()
            
            # If price looks good, get quote
            quote_resp = await client.get(
                f"{api_url}/swap/permit2/quote",
                params={
                    "sellToken": from_token_param,
                    "buyToken": to_token_param,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": wallet_address,
                    "slippageBps": "100"  # Default 1% slippage
                }
            )
            quote_resp.raise_for_status()
            quote_data = quote_resp.json()
            
            # Format response in standardized format
            return {
                "success": True,
                "protocol": "0x",
                "buyAmount": quote_data.get("buyAmount"),
                "sellAmount": sell_amount,
                "rate": float(quote_data.get("price", 0)),
                "minBuyAmount": quote_data.get("minBuyAmount", "0"),
                "estimatedGas": quote_data.get("gas", "0"),
                "transaction": {
                    "to": quote_data.get("transaction", {}).get("to", ""),
                    "data": quote_data.get("transaction", {}).get("data", ""),
                    "value": quote_data.get("transaction", {}).get("value", "0"),
                    "chainId": chain_id
                },
                "metadata": {
                    "gasPrice": quote_data.get("gasPrice"),
                    "permit2": quote_data.get("permit2"),
                    "zid": quote_data.get("zid"),
                    "source": "0x",
                    "from_token": {
                        "address": from_address,
                        "symbol": from_token.symbol,
                        "decimals": from_token.decimals
                    },
                    "to_token": {
                        "address": to_address,
                        "symbol": to_token.symbol,
                        "decimals": to_token.decimals
                    }
                }
            }
        except httpx.HTTPStatusError as e:
            raise ValueError(f"0x API error: {e.response.text}")
    
    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
    ) -> Dict[str, Any]:
        """Build transaction from quote."""
        # 0x quotes already include transaction data
        if "transaction" not in quote:
            raise ValueError("Invalid quote format - missing transaction data")
            
        tx_data = quote["transaction"]
        return {
            "to": tx_data.get("to", ""),
            "data": tx_data.get("data", ""),
            "value": tx_data.get("value", "0"),
            "gas_limit": quote.get("estimatedGas", "500000"),
            "chainId": chain_id
        } 