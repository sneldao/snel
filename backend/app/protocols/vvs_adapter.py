"""
VVS Finance adapter implementation for Cronos.
VVS Finance is the leading DEX on Cronos with 64.6% volume share.
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


class VVSAdapter:
    """
    VVS Finance adapter for Cronos.
    
    VVS Finance is a Uniswap V2 fork and the dominant DEX on Cronos.
    Uses direct on-chain calls via RPC for quotes and transactions.
    """

    # VVS Finance contract addresses
    ROUTER_ADDRESSES = {
        25: "0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae",   # Cronos Mainnet
        338: "0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae",  # Cronos Testnet
    }
    
    FACTORY_ADDRESSES = {
        25: "0x3B44B2a187a7b3824131F8db5a74194D0a42Fc15",   # Cronos Mainnet
        338: "0x3B44B2a187a7b3824131F8db5a74194D0a42Fc15",  # Cronos Testnet
    }

    def __init__(self):
        """Initialize the VVS Finance adapter."""
        self.http_client = None
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._quote_ttl_seconds: int = 10

    @property
    def protocol_id(self) -> str:
        return "vvs"

    @property
    def name(self) -> str:
        return "VVS Finance"

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

    async def _get_pair_address(self, token_a: str, token_b: str, chain_id: int) -> Optional[str]:
        """Get pair address from VVS Factory."""
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
            logger.debug(f"Failed to get pair address: {e}")
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
        """Calculate output amount using Uniswap V2 formula with 0.25% fee."""
        if reserve_in == 0 or reserve_out == 0:
            return 0
        
        # VVS Finance uses 0.25% fee (997/1000)
        amount_in_with_fee = amount_in * 997
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        
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
        """Get swap quote from VVS Finance."""
        try:
            if not self.is_supported(chain_id):
                raise ValueError(f"Chain {chain_id} not supported by VVS Finance")

            if to_chain_id is not None and to_chain_id != chain_id:
                raise ValueError("VVS Finance only supports same-chain swaps")

            # Get token addresses
            from_address = from_token.get_address(chain_id)
            to_address = to_token.get_address(chain_id)
            
            if not from_address or not to_address:
                raise ProtocolError(
                    message="Token addresses missing for this chain",
                    protocol="vvs",
                    user_message=f"VVS Finance does not support {from_token.symbol} or {to_token.symbol} on Cronos",
                )

            # Handle native CRO token - convert to WCRO for pair lookups
            wcro_address = "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23"  # WCRO address
            is_from_native = from_token.type == TokenType.NATIVE and from_token.symbol == "CRO"
            is_to_native = to_token.type == TokenType.NATIVE and to_token.symbol == "CRO"
            
            # For pair lookups, always use WCRO instead of native CRO
            pair_from_address = from_address
            pair_to_address = to_address
            
            if from_address == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
                pair_from_address = wcro_address
            if to_address == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
                pair_to_address = wcro_address

            # Convert amount to wei
            amount_wei = int(amount * (Decimal(10) ** from_token.decimals))
            
            logger.info(f"VVS quote: {from_token.symbol} ({from_address}) -> {to_token.symbol} ({to_address})")
            logger.info(f"Pair lookup: {pair_from_address} -> {pair_to_address}")
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
                # Provide helpful suggestions for Cronos users
                if chain_id == 25:  # Cronos Mainnet
                    if from_token.symbol == "CRO" and to_token.symbol == "USDC":
                        suggestion = "CRO/USDC pair not available on VVS Finance. Try CRO/USDT instead, which has good liquidity."
                    elif from_token.symbol == "USDC" and to_token.symbol == "CRO":
                        suggestion = "USDC/CRO pair not available on VVS Finance. Try USDT/CRO instead, which has good liquidity."
                    else:
                        suggestion = f"No liquidity pool found for {from_token.symbol}/{to_token.symbol}. Popular pairs on VVS Finance include CRO/USDT, CRO/ETH."
                else:
                    suggestion = f"No liquidity pool found for {from_token.symbol}/{to_token.symbol} on VVS Finance"
                
                raise ProtocolError(
                    message="No VVS Finance pair found for this token combination",
                    protocol="vvs",
                    user_message=suggestion,
                )

            # Get reserves
            reserves = await self._get_reserves(pair_address, chain_id)
            if not reserves:
                raise ProtocolError(
                    message="Failed to get pair reserves",
                    protocol="vvs",
                    user_message="Unable to fetch liquidity data from VVS Finance",
                )

            reserve0, reserve1 = reserves
            
            # Determine token order (pairs are ordered by address)
            token0_is_from = pair_from_address.lower() < pair_to_address.lower()
            reserve_in = reserve0 if token0_is_from else reserve1
            reserve_out = reserve1 if token0_is_from else reserve0

            # Check for sufficient liquidity
            if reserve_in == 0 or reserve_out == 0:
                raise ProtocolError(
                    message="Insufficient liquidity in VVS Finance pair",
                    protocol="vvs",
                    user_message=f"No liquidity available for {from_token.symbol}/{to_token.symbol} on VVS Finance",
                )

            # Calculate output amount
            amount_out_wei = self._calculate_amount_out(amount_wei, reserve_in, reserve_out)
            
            if amount_out_wei == 0:
                raise ProtocolError(
                    message="Calculated output amount is zero",
                    protocol="vvs",
                    user_message="Trade amount too small or insufficient liquidity",
                )

            # Convert back to decimal
            amount_out_decimal = Decimal(amount_out_wei) / (Decimal(10) ** to_token.decimals)
            rate = float(amount_out_decimal / amount) if amount > 0 else 0.0

            # Estimate gas (typical for Uniswap V2 swap)
            estimated_gas = 150000

            data = {
                "success": True,
                "protocol": "vvs",
                "router_address": self.ROUTER_ADDRESSES[chain_id],
                "pair_address": pair_address,
                "from_address": pair_from_address,  # Use WCRO for pair interactions
                "to_address": pair_to_address,      # Use WCRO for pair interactions
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
            logger.exception(f"Error getting VVS quote: {e}")
            return {
                "success": False,
                "error": f"Failed to get VVS Finance quote: {str(e)}",
                "protocol": "vvs"
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
    ) -> Dict[str, Any]:
        """Build swap transaction for VVS Finance."""
        try:
            if not quote.get("success", False):
                raise ValueError("Invalid quote")

            router_address = self.ROUTER_ADDRESSES.get(chain_id)
            if not router_address:
                raise ValueError(f"No VVS router for chain {chain_id}")

            from_address = quote["from_address"]
            to_address = quote["to_address"]
            amount_in = int(quote["amount_in_wei"])
            amount_out_min = int(int(quote["amount_out_wei"]) * 0.95)  # 5% slippage tolerance
            recipient = quote["wallet_address"]
            
            # Deadline (30 minutes from now)
            deadline = int(time.time()) + 1800

            # Check if this involves native CRO
            wcro_address = "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23"
            is_from_native = quote.get("from_token_native", False)
            is_to_native = quote.get("to_token_native", False)

            if is_from_native:
                # swapExactETHForTokens(uint amountOutMin, address[] calldata path, address to, uint deadline)
                selector = function_signature_to_4byte_selector("swapExactETHForTokens(uint256,address[],address,uint256)").hex()
                path = [wcro_address, to_address]
                encoded = abi_encode(
                    ["uint256", "address[]", "address", "uint256"],
                    [amount_out_min, path, to_checksum_address(recipient), deadline]
                ).hex()
                data = "0x" + selector + encoded
                value = hex(amount_in)
            elif is_to_native:
                # swapExactTokensForETH(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline)
                selector = function_signature_to_4byte_selector("swapExactTokensForETH(uint256,uint256,address[],address,uint256)").hex()
                path = [from_address, wcro_address]
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
            logger.exception(f"Error building VVS transaction: {e}")
            return {
                "error": f"Failed to build VVS Finance transaction: {str(e)}",
                "technical_details": str(e)
            }


# Create instance
vvs_adapter = VVSAdapter()