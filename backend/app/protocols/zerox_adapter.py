"""
0x Protocol adapter implementation.
"""
import os
import hashlib
import httpx
import asyncio
import time
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from app.models.token import TokenInfo, TokenType
from eth_abi import encode
from app.config.chains import get_chains_by_protocol, get_chain_info

logger = logging.getLogger(__name__)


class ZeroXAdapter:
    """0x Protocol adapter."""
    
    # Unified API endpoint for v2
    BASE_URL = "https://api.0x.org"

    # Supported chains will be derived from config
    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs dynamically from config."""
        return [c.id for c in get_chains_by_protocol("0x")]
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 0.5  # seconds
    QUOTE_CACHE_TTL = 8  # seconds

    def __init__(self):
        """Initialize the 0x protocol adapter."""
        self.api_key = os.getenv("ZEROX_API_KEY", "")
        if not self.api_key:
            logger.warning("ZEROX_API_KEY not set, 0x adapter will fail at request time")
        
        self.http_client = None
        # Quote cache with TTL
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        # Request deduplication
        self._pending_requests: Dict[str, asyncio.Task] = {}

    @property
    def protocol_id(self) -> str:
        return "0x"
    
    @property
    def name(self) -> str:
        return "0x Protocol"
    
    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        return chain_id in self.supported_chains
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            headers = {"0x-version": "v2"}
            if self.api_key:
                headers["0x-api-key"] = self.api_key
            
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers=headers
            )
        return self.http_client
    
    def _make_cache_key(self, from_token: str, to_token: str, amount: str, chain_id: int) -> str:
        """Create a cache key for a quote."""
        key_str = f"{from_token}:{to_token}:{amount}:{chain_id}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _with_retry(self, coro) -> Any:
        """Execute coroutine with exponential backoff retry."""
        delay = self.INITIAL_RETRY_DELAY
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return await asyncio.wait_for(coro(), timeout=15.0)
            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    logger.debug(f"Request timeout (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {delay}s")
                    await asyncio.sleep(delay)
                    delay *= 2
            except httpx.HTTPStatusError as e:
                # Retry on 429 (rate limit) and 5xx errors
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    last_error = e
                    if attempt < self.MAX_RETRIES - 1:
                        logger.debug(f"HTTP {e.response.status_code} (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {delay}s")
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        raise ValueError(f"0x API error after {self.MAX_RETRIES} attempts: {e.response.text}")
                else:
                    raise ValueError(f"0x API error: {e.response.text}")
            except Exception as e:
                # Don't retry on other exceptions
                raise
        
        raise last_error or RuntimeError("Request failed after retries")
    
    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
    
    def get_api_url(self, chain_id: int) -> str:
        """Get API URL (unified for v2)."""
        return self.BASE_URL
    
    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        to_chain_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get swap quote from 0x API with caching and retry logic."""
        if not self.is_supported(chain_id):
            raise ValueError(f"Chain {chain_id} not supported by 0x protocol")
        
        # Get token addresses for this chain
        from_address = from_token.get_address(chain_id)
        to_address = to_token.get_address(chain_id)
        
        if not from_address or not to_address:
            raise ValueError(f"One or both tokens not supported on chain {chain_id}")
        
        # Convert to sell amount with proper decimals
        sell_amount = int(amount * (Decimal(10) ** from_token.decimals))
        
        # Check cache first
        cache_key = self._make_cache_key(from_address, to_address, str(sell_amount), chain_id)
        now = time.time()
        cached = self._quote_cache.get(cache_key)
        if cached and (now - cached.get("ts", 0) <= self.QUOTE_CACHE_TTL):
            logger.debug(f"Cache hit for quote {from_token.symbol}->{to_token.symbol}")
            return cached["data"]
        
        # Check for pending identical request (deduplication)
        if cache_key in self._pending_requests:
            logger.debug(f"Request deduplication: waiting for existing quote request")
            return await self._pending_requests[cache_key]
        
        # Create and store task for deduplication
        async def fetch_quote():
            try:
                return await self._fetch_quote_with_retry(
                    from_token, to_token, sell_amount, chain_id, wallet_address, from_address, to_address
                )
            finally:
                # Clean up pending request
                self._pending_requests.pop(cache_key, None)
        
        task = asyncio.create_task(fetch_quote())
        self._pending_requests[cache_key] = task
        
        try:
            result = await task
            # Cache successful result
            self._quote_cache[cache_key] = {"ts": now, "data": result}
            return result
        except Exception:
            # Don't cache errors
            raise
    
    async def _fetch_quote_with_retry(
        self, from_token: TokenInfo, to_token: TokenInfo, sell_amount: int, chain_id: int,
        wallet_address: str, from_address: str, to_address: str
    ) -> Dict[str, Any]:
        """Fetch quote from 0x API with retry logic."""
        # Convert token addresses to 0x API format
        from_token_param = "ETH" if from_token.type == TokenType.NATIVE else from_address
        to_token_param = "ETH" if to_token.type == TokenType.NATIVE else to_address
        
        api_url = self.get_api_url(chain_id)
        client = await self._get_client()
        
        if not self.api_key:
            raise ValueError("ZEROX_API_KEY not configured")
        
        # Fetch quote with retry
        async def do_request():
            # Get price quote first
            price_resp = await client.get(
                f"{api_url}/swap/allowance-holder/price",
                params={
                    "sellToken": from_token_param,
                    "buyToken": to_token_param,
                    "sellAmount": str(sell_amount),
                    "chainId": chain_id,
                    "taker": wallet_address
                }
            )
            price_resp.raise_for_status()

            # If price looks good, get full quote
            quote_resp = await client.get(
                f"{api_url}/swap/allowance-holder/quote",
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
            return quote_resp.json()
        
        quote_data = await self._with_retry(do_request)
        
        # Validate response structure
        if not quote_data.get("transaction"):
            raise ValueError("Invalid 0x quote: missing transaction data")
        
        tx = quote_data["transaction"]
        if not all(k in tx for k in ["to", "data"]):
            raise ValueError("Invalid 0x quote: incomplete transaction data")
        
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
                "to": tx.get("to", ""),
                "data": tx.get("data", ""),
                "value": tx.get("value", "0"),
                "chainId": chain_id
            },
            "metadata": {
                "gasPrice": quote_data.get("gasPrice"),
                "allowanceTarget": quote_data.get("allowanceTarget"),
                "allowanceIssues": quote_data.get("issues", {}).get("allowance") if quote_data.get("issues") else None,
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
            "gasLimit": quote.get("estimatedGas", "500000"),
            "chainId": chain_id
        }

    def create_approval_transaction(
        self,
        token_address: str,
        spender_address: str,
        amount: str,
        chain_id: int,
    ) -> Dict[str, Any]:
        """Create an ERC20 approval transaction."""
        # ERC20 approve function signature: approve(address spender, uint256 amount)
        function_selector = "0x095ea7b3"  # approve(address,uint256)

        # Encode the parameters
        encoded_params = encode(
            ['address', 'uint256'],
            [spender_address, int(amount)]
        ).hex()

        # Combine function selector and encoded parameters
        data = function_selector + encoded_params

        return {
            "to": token_address,
            "data": data,
            "value": "0",
            "gas_limit": "100000",  # Standard gas limit for approval
            "chainId": chain_id
        }