"""
MM Finance adapter implementation for Cronos.
MM Finance has WCRO/USDC pairs with 60% trading volume using specific token addresses.
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
import httpx
import asyncio
import time
from eth_abi import encode as abi_encode, decode as abi_decode
from eth_utils import function_signature_to_4byte_selector, to_checksum_address

from app.models.token import TokenInfo, TokenType
from app.core.errors import ProtocolError

logger = logging.getLogger(__name__)


class MMAdapter:
    """
    MM Finance adapter for Cronos.
    
    MM Finance has WCRO/USDC pairs with 60% trading volume.
    Uses specific token addresses different from standard ones.
    """

    # MM Finance contract addresses (corrected based on official documentation)
    ROUTER_ADDRESSES = {
        25: "0x145677FC4d9b8F19B5D56d1820c48e0443049a30",   # MM Finance Router (MeerkatRouter)
        338: "0x145677FC4d9b8F19B5D56d1820c48e0443049a30",  # Cronos Testnet (assumed same)
    }
    
    FACTORY_ADDRESSES = {
        25: "0xd590cC180601AEcD6eeADD9B7f2B7611519544f4",   # MM Finance Factory
        338: "0xd590cC180601AEcD6eeADD9B7f2B7611519544f4",  # Cronos Testnet (assumed same)
    }

    # MM Finance specific token addresses (from official Cronos documentation)
    MM_TOKEN_ADDRESSES = {
        25: {
            "USDC": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",  # Official Cronos USDC
            "WCRO": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Official Cronos WCRO
        },
        338: {
            "USDC": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",  # Official Cronos USDC (testnet)
            "WCRO": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Official Cronos WCRO (testnet)
        }
    }

    def __init__(self):
        """Initialize the MM Finance adapter."""
        self.http_client = None
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._quote_ttl_seconds: int = 10

    @property
    def protocol_id(self) -> str:
        return "mm"

    @property
    def name(self) -> str:
        return "MM Finance"

    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return [25, 338]  # Cronos Mainnet and Testnet

    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        return chain_id in self.supported_chains

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client

    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    async def _rpc_call(self, rpc_url: str, payload: Dict[str, Any], timeout: float = 15.0) -> Any:
        """Perform RPC call."""
        client = await self._get_client()
        try:
            resp = await client.post(rpc_url, json=payload, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                raise RuntimeError(result["error"].get("message", "RPC error"))
            return result.get("result")
        except Exception as e:
            logger.error(f"RPC call failed: {e}")
            raise

    def _get_mm_token_address(self, token_symbol: str, chain_id: int) -> Optional[str]:
        """Get MM Finance specific token address."""
        chain_tokens = self.MM_TOKEN_ADDRESSES.get(chain_id, {})
        return chain_tokens.get(token_symbol.upper())

    def _should_use_mm_finance(self, from_token: TokenInfo, to_token: TokenInfo) -> bool:
        """Determine if MM Finance should be used for this token pair."""
        # MM Finance specializes in USDC pairs
        symbols = {from_token.symbol.upper(), to_token.symbol.upper()}
        return "USDC" in symbols and ("CRO" in symbols or "WCRO" in symbols)

    async def _get_pair_address(self, token_a: str, token_b: str, chain_id: int) -> Optional[str]:
        """Get pair address from MM Finance Factory."""
        try:
            factory_address = self.FACTORY_ADDRESSES.get(chain_id)
            if not factory_address:
                return None

            # getPair(address,address) function
            selector = function_signature_to_4byte_selector("getPair(address,address)").hex()
            encoded = abi_encode(["address", "address"], [token_a, token_b]).hex()
            data = "0x" + selector + encoded

            rpc_url = "https://evm.cronos.org" if chain_id == 25 else "https://evm-t3.cronos.org"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": factory_address, "data": data}, "latest"]
            }

            result = await self._rpc_call(rpc_url, payload)
            if result and result != "0x":
                decoded = abi_decode(["address"], bytes.fromhex(result[2:]))
                pair_address = decoded[0]
                if pair_address != "0x0000000000000000000000000000000000000000":
                    return pair_address
            return None
        except Exception as e:
            logger.debug(f"Failed to get MM Finance pair address: {e}")
            return None

    async def _get_reserves(self, pair_address: str, chain_id: int) -> Optional[tuple]:
        """Get reserves from pair contract."""
        try:
            # getReserves() function
            selector = function_signature_to_4byte_selector("getReserves()").hex()
            data = "0x" + selector

            rpc_url = "https://evm.cronos.org" if chain_id == 25 else "https://evm-t3.cronos.org"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": pair_address, "data": data}, "latest"]
            }

            result = await self._rpc_call(rpc_url, payload)
            if result and result != "0x":
                # Returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)
                decoded = abi_decode(["uint112", "uint112", "uint32"], bytes.fromhex(result[2:]))
                return decoded[0], decoded[1]  # reserve0, reserve1
            return None
        except Exception as e:
            logger.debug(f"Failed to get reserves: {e}")
            return None

    def _calculate_amount_out(self, amount_in: int, reserve_in: int, reserve_out: int) -> int:
        """Calculate output amount using Uniswap V2 formula with 0.17% fee."""
        if reserve_in == 0 or reserve_out == 0:
            return 0
        
        # MM Finance uses 0.17% fee (9983/10000)
        amount_in_with_fee = amount_in * 9983
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 10000) + amount_in_with_fee
        
        return numerator // denominator

    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        to_chain_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get swap quote from MM Finance."""
        try:
            if not self.is_supported(chain_id):
                raise ValueError(f"Chain {chain_id} not supported by MM Finance")

            if to_chain_id is not None and to_chain_id != chain_id:
                raise ValueError("MM Finance only supports same-chain swaps")

            # Check if this pair should use MM Finance
            if not self._should_use_mm_finance(from_token, to_token):
                raise ProtocolError(
                    message="MM Finance specializes in USDC pairs",
                    protocol="mm",
                    user_message=f"MM Finance specializes in USDC pairs. For {from_token.symbol}/{to_token.symbol}, try VVS Finance instead.",
                )

            # Get MM Finance specific token addresses
            from_address = from_token.get_address(chain_id)
            to_address = to_token.get_address(chain_id)
            
            # Override with MM Finance specific addresses for USDC and CRO
            if from_token.symbol.upper() == "USDC":
                mm_usdc = self._get_mm_token_address("USDC", chain_id)
                if mm_usdc:
                    from_address = mm_usdc
                    
            if to_token.symbol.upper() == "USDC":
                mm_usdc = self._get_mm_token_address("USDC", chain_id)
                if mm_usdc:
                    to_address = mm_usdc
            
            if not from_address or not to_address:
                raise ProtocolError(
                    message="Token addresses missing for this chain",
                    protocol="mm",
                    user_message=f"MM Finance does not support {from_token.symbol} or {to_token.symbol} on Cronos",
                )

            # Handle native CRO token - convert to MM Finance WCRO
            mm_wcro = self._get_mm_token_address("WCRO", chain_id)
            is_from_native = from_token.type == TokenType.NATIVE and from_token.symbol == "CRO"
            is_to_native = to_token.type == TokenType.NATIVE and to_token.symbol == "CRO"
            
            # For pair lookups, use MM Finance specific WCRO
            pair_from_address = from_address
            pair_to_address = to_address
            
            if from_address == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE" and mm_wcro:
                pair_from_address = mm_wcro
            if to_address == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE" and mm_wcro:
                pair_to_address = mm_wcro

            # Convert amount to wei
            amount_wei = int(amount * (Decimal(10) ** from_token.decimals))
            
            logger.info(f"MM Finance quote: {from_token.symbol} -> {to_token.symbol}")
            logger.info(f"Using MM Finance addresses: {pair_from_address} -> {pair_to_address}")
            logger.info(f"Amount: {amount} {from_token.symbol} = {amount_wei} wei")

            # Cache key
            cache_key = f"{chain_id}:{pair_from_address}:{pair_to_address}:{amount_wei}"
            cached = self._quote_cache.get(cache_key)
            now = int(time.time())
            if cached and (now - cached.get("ts", 0) <= self._quote_ttl_seconds):
                return cached["data"]

            # Get pair address
            pair_address = await self._get_pair_address(pair_from_address, pair_to_address, chain_id)
            if not pair_address:
                raise ProtocolError(
                    message="No MM Finance pair found for this token combination",
                    protocol="mm",
                    user_message=f"WCRO/USDC pair not found on MM Finance. This pair should have 60% of trading volume. Please verify token addresses.",
                )

            # Get reserves
            reserves = await self._get_reserves(pair_address, chain_id)
            if not reserves:
                raise ProtocolError(
                    message="Failed to get pair reserves",
                    protocol="mm",
                    user_message="Unable to fetch liquidity data from MM Finance",
                )

            reserve0, reserve1 = reserves
            
            # Determine token order (pairs are ordered by address)
            token0_is_from = pair_from_address.lower() < pair_to_address.lower()
            reserve_in = reserve0 if token0_is_from else reserve1
            reserve_out = reserve1 if token0_is_from else reserve0

            # Check for sufficient liquidity
            if reserve_in == 0 or reserve_out == 0:
                raise ProtocolError(
                    message="Insufficient liquidity in MM Finance pair",
                    protocol="mm",
                    user_message=f"No liquidity available for {from_token.symbol}/{to_token.symbol} on MM Finance",
                )

            # Calculate output amount
            amount_out_wei = self._calculate_amount_out(amount_wei, reserve_in, reserve_out)
            
            if amount_out_wei == 0:
                raise ProtocolError(
                    message="Calculated output amount is zero",
                    protocol="mm",
                    user_message="Trade amount too small or insufficient liquidity",
                )

            # Convert back to decimal
            amount_out_decimal = Decimal(amount_out_wei) / (Decimal(10) ** to_token.decimals)
            rate = float(amount_out_decimal / amount) if amount > 0 else 0.0

            # Estimate gas (typical for Uniswap V2 swap)
            estimated_gas = 150000

            data = {
                "success": True,
                "protocol": "mm",
                "router_address": self.ROUTER_ADDRESSES[chain_id],
                "pair_address": pair_address,
                "from_address": pair_from_address,  # Use MM Finance addresses for pair interactions
                "to_address": pair_to_address,      # Use MM Finance addresses for pair interactions
                "original_from_address": from_address,  # Keep original for display
                "original_to_address": to_address,      # Keep original for display
                "from_amount": str(amount),
                "to_amount": str(amount_out_decimal),
                "sellAmount": str(amount_wei),
                "buyAmount": str(amount_out_wei),
                "amount_in_wei": amount_wei,
                "amount_out_wei": amount_out_wei,
                "rate": rate,
                "chain_id": chain_id,
                "wallet_address": wallet_address,
                "estimatedGas": str(estimated_gas),
                "reserves": {
                    "reserve0": reserve0,
                    "reserve1": reserve1,
                    "token0_is_from": token0_is_from
                },
                "from_token_native": is_from_native,
                "to_token_native": is_to_native
            }
            
            # Cache the result
            self._quote_cache[cache_key] = {"ts": now, "data": data}
            return data

        except Exception as e:
            logger.exception(f"Error getting MM Finance quote: {e}")
            return {
                "success": False,
                "error": f"Failed to get MM Finance quote: {str(e)}",
                "protocol": "mm"
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
    ) -> Dict[str, Any]:
        """Build swap transaction for MM Finance."""
        try:
            if not quote.get("success", False):
                raise ValueError("Invalid quote")

            router_address = self.ROUTER_ADDRESSES.get(chain_id)
            if not router_address:
                raise ValueError(f"No MM Finance router for chain {chain_id}")

            from_address = quote["from_address"]
            to_address = quote["to_address"]
            amount_in = int(quote["amount_in_wei"])
            amount_out_min = int(int(quote["amount_out_wei"]) * 0.95)  # 5% slippage tolerance
            recipient = quote["wallet_address"]
            
            # Deadline (30 minutes from now)
            deadline = int(time.time()) + 1800

            # Check if this involves native CRO
            is_from_native = quote.get("from_token_native", False)
            is_to_native = quote.get("to_token_native", False)
            mm_wcro = self._get_mm_token_address("WCRO", chain_id)

            if is_from_native and mm_wcro:
                # swapExactETHForTokens(uint amountOutMin, address[] calldata path, address to, uint deadline)
                selector = function_signature_to_4byte_selector("swapExactETHForTokens(uint256,address[],address,uint256)").hex()
                path = [mm_wcro, to_address]
                encoded = abi_encode(
                    ["uint256", "address[]", "address", "uint256"],
                    [amount_out_min, path, to_checksum_address(recipient), deadline]
                ).hex()
                data = "0x" + selector + encoded
                value = hex(amount_in)
            elif is_to_native and mm_wcro:
                # swapExactTokensForETH(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline)
                selector = function_signature_to_4byte_selector("swapExactTokensForETH(uint256,uint256,address[],address,uint256)").hex()
                path = [from_address, mm_wcro]
                encoded = abi_encode(
                    ["uint256", "uint256", "address[]", "address", "uint256"],
                    [amount_in, amount_out_min, path, to_checksum_address(recipient), deadline]
                ).hex()
                data = "0x" + selector + encoded
                value = "0x0"
            else:
                # swapExactTokensForTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline)
                selector = function_signature_to_4byte_selector("swapExactTokensForTokens(uint256,uint256,address[],address,uint256)").hex()
                path = [from_address, to_address]
                encoded = abi_encode(
                    ["uint256", "uint256", "address[]", "address", "uint256"],
                    [amount_in, amount_out_min, path, to_checksum_address(recipient), deadline]
                ).hex()
                data = "0x" + selector + encoded
                value = "0x0"

            return {
                "to": router_address,
                "data": data,
                "value": value,
                "gasLimit": quote.get("estimatedGas", "150000"),
                "chainId": chain_id
            }

        except Exception as e:
            logger.exception(f"Error building MM Finance transaction: {e}")
            return {
                "error": f"Failed to build MM Finance transaction: {str(e)}",
                "technical_details": str(e)
            }


# Create instance
mm_adapter = MMAdapter()