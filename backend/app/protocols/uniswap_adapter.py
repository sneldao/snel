"""
Uniswap V3 protocol adapter with concentrated liquidity optimization and permit2 integration.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import hashlib
import httpx
import time
import asyncio
from eth_abi import decode as decode_abi, encode as abi_encode
from eth_utils import function_signature_to_4byte_selector, to_checksum_address

from app.models.token import TokenInfo
from .permit2_handler import Permit2Handler, Permit2Data

# Rate limiting and circuit breaker constants
_RATE_LIMIT_WINDOW = 1.0  # seconds
_MAX_REQUESTS_PER_WINDOW = 10
_FAILURE_THRESHOLD = 5
_COOLDOWN_SECONDS = 30

logger = logging.getLogger(__name__)

class UniswapAdapter:
    """Uniswap V3 protocol adapter."""

    # Uniswap V3 Router addresses by chain (kept for backward-compat; primary is config_manager)
    ROUTER_ADDRESSES = {
        1: "0xE592427A0AEce92De3Edee1F18E0157C05861564",      # Ethereum
        8453: "0x2626664c2603336E57B271c5C0b26F421741e481",    # Base
        42161: "0xE592427A0AEce92De3Edee1F18E0157C05861564",   # Arbitrum
        10: "0xE592427A0AEce92De3Edee1F18E0157C05861564",      # Optimism
        137: "0xE592427A0AEce92De3Edee1F18E0157C05861564",     # Polygon
    }

    # Deprecated: prefer config_manager token addresses
    TOKEN_ADDRESSES = {
        8453: {
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "WETH": "0x4200000000000000000000000000000000000006",
            "ETH": "0x4200000000000000000000000000000000000006",
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
        }
    }

    def __init__(self):
        """Initialize the Uniswap protocol adapter."""
        self.http_client = None
        # Simple in-memory TTL cache for quotes
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._quote_ttl_seconds: int = 8
        # Permit2 handler for EIP-712 signature support
        self.permit2_handler = Permit2Handler()
        # V3 concentrated liquidity optimization
        self._pool_cache: Dict[str, Dict[str, Any]] = {}
        self._pool_ttl_seconds: int = 300  # 5 minutes for pool data
        # Instance-level RPC state tracking (thread-safe per instance)
        self._rpc_state: Dict[str, Dict[str, Any]] = {}
        # Request deduplication to avoid parallel identical requests
        self._pending_requests: Dict[str, asyncio.Task] = {}

    @property
    def protocol_id(self) -> str:
        return "uniswap"

    @property
    def name(self) -> str:
        return "Uniswap V3"

    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return list(self.ROUTER_ADDRESSES.keys())

    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        return chain_id in self.supported_chains

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client

    async def _apply_rate_limit(self, rpc_url: str):
        """Enforce simple rate limiting per RPC URL."""
        state = self._rpc_state.setdefault(rpc_url, {"timestamps": [], "failures": 0, "circuit_open": False, "circuit_opened_at": 0})
        now = time.time()
        # Remove timestamps outside the window
        state["timestamps"] = [t for t in state["timestamps"] if now - t < _RATE_LIMIT_WINDOW]
        if len(state["timestamps"]) >= _MAX_REQUESTS_PER_WINDOW:
            # Sleep until earliest timestamp exits the window
            sleep_time = _RATE_LIMIT_WINDOW - (now - min(state["timestamps"]))
            await asyncio.sleep(sleep_time)
        state["timestamps"].append(time.time())

    def _record_failure(self, rpc_url: str):
        """Record a failure and open circuit if threshold exceeded."""
        state = self._rpc_state.setdefault(rpc_url, {"timestamps": [], "failures": 0, "circuit_open": False, "circuit_opened_at": 0})
        state["failures"] += 1
        if state["failures"] >= _FAILURE_THRESHOLD:
            state["circuit_open"] = True
            state["circuit_opened_at"] = time.time()

    def _reset_circuit(self, rpc_url: str):
        """Reset circuit after cooldown."""
        state = self._rpc_state.get(rpc_url)
        if state and state["circuit_open"]:
            if time.time() - state["circuit_opened_at"] >= _COOLDOWN_SECONDS:
                state["circuit_open"] = False
                state["failures"] = 0

    async def _rpc_call(self, rpc_url: str, payload: Dict[str, Any], timeout: float = 15.0) -> Any:
        """Perform RPC call with rate limiting and circuit breaker."""
        self._reset_circuit(rpc_url)
        state = self._rpc_state.get(rpc_url, {})
        if state.get("circuit_open"):
            raise RuntimeError(f"Circuit open for RPC {rpc_url}")

        await self._apply_rate_limit(rpc_url)
        client = await self._get_client()
        try:
            resp = await client.post(rpc_url, json=payload, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                self._record_failure(rpc_url)
                raise RuntimeError(result["error"].get("message", "RPC error"))
            # Successful call, reset failures
            if state:
                state["failures"] = 0
            return result.get("result")
        except asyncio.TimeoutError:
            self._record_failure(rpc_url)
            raise RuntimeError(f"RPC call timeout after {timeout}s")
        except Exception as e:
            self._record_failure(rpc_url)
            raise e
 

    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    def _get_token_address(self, token_symbol: str, chain_id: int) -> str:
        """Get token address for a given symbol and chain."""
        chain_tokens = self.TOKEN_ADDRESSES.get(chain_id, {})
        return chain_tokens.get(token_symbol.upper(), "")

    async def _get_pool_liquidity(self, token0: str, token1: str, fee: int, chain_id: int, rpc_urls: List[str]) -> Optional[Dict[str, Any]]:
        """Get pool liquidity and state for concentrated liquidity optimization."""
        try:
            from app.core.config_manager import config_manager
            uni_cfg = await config_manager.get_protocol("uniswap")
            if not uni_cfg:
                return None
            
            contracts = uni_cfg.contract_addresses.get(chain_id, {})
            factory = contracts.get("factory")
            if not factory:
                return None

            # Cache key for pool data
            cache_key = f"{chain_id}:{token0}:{token1}:{fee}"
            cached = self._pool_cache.get(cache_key)
            now = int(time.time())
            if cached and (now - cached.get("ts", 0) <= self._pool_ttl_seconds):
                return cached["data"]

            # Get pool address from factory
            selector = function_signature_to_4byte_selector("getPool(address,address,uint24)").hex()
            encoded = abi_encode(["address", "address", "uint24"], [token0, token1, fee]).hex()
            data = "0x" + selector + encoded

            pool_address = None
            for rpc_url in rpc_urls:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": factory, "data": data}, "latest"]
                }
                try:
                    result = await self._rpc_call(rpc_url, payload)
                    if result and result != "0x":
                        decoded = decode_abi(["address"], bytes.fromhex(result[2:]))
                        pool_address = decoded[0]
                        if pool_address != "0x0000000000000000000000000000000000000000":
                            break
                except Exception:
                    continue

            if not pool_address or pool_address == "0x0000000000000000000000000000000000000000":
                return None

            # Get pool liquidity and tick data
            liquidity_selector = function_signature_to_4byte_selector("liquidity()").hex()
            slot0_selector = function_signature_to_4byte_selector("slot0()").hex()

            liquidity_data = "0x" + liquidity_selector
            slot0_data = "0x" + slot0_selector

            liquidity = None
            sqrt_price_x96 = None
            tick = None

            for rpc_url in rpc_urls:
                try:
                    # Batch call for efficiency
                    batch_payload = [
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "eth_call",
                            "params": [{"to": pool_address, "data": liquidity_data}, "latest"]
                        },
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "eth_call",
                            "params": [{"to": pool_address, "data": slot0_data}, "latest"]
                        }
                    ]
                    
                    client = await self._get_client()
                    resp = await client.post(rpc_url, json=batch_payload, timeout=15.0)
                    resp.raise_for_status()
                    results = resp.json()
                    
                    if isinstance(results, list) and len(results) >= 2:
                        # Parse liquidity
                        if results[0].get("result") and results[0]["result"] != "0x":
                            liquidity_decoded = decode_abi(["uint128"], bytes.fromhex(results[0]["result"][2:]))
                            liquidity = liquidity_decoded[0]
                        
                        # Parse slot0 (sqrtPriceX96, tick, observationIndex, observationCardinality, observationCardinalityNext, feeProtocol, unlocked)
                        if results[1].get("result") and results[1]["result"] != "0x":
                            slot0_decoded = decode_abi(
                                ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"],
                                bytes.fromhex(results[1]["result"][2:])
                            )
                            sqrt_price_x96, tick = slot0_decoded[0], slot0_decoded[1]
                        
                        if liquidity is not None and sqrt_price_x96 is not None:
                            break
                except Exception:
                    continue

            if liquidity is None or sqrt_price_x96 is None:
                return None

            pool_data = {
                "pool_address": pool_address,
                "liquidity": liquidity,
                "sqrt_price_x96": sqrt_price_x96,
                "tick": tick,
                "fee": fee
            }
            
            # Cache the result
            self._pool_cache[cache_key] = {"ts": now, "data": pool_data}
            return pool_data

        except Exception as e:
            logger.debug(f"Failed to get pool liquidity for {token0}/{token1} fee {fee}: {e}")
            return None

    async def _optimize_fee_tier_selection(self, token0: str, token1: str, chain_id: int, rpc_urls: List[str]) -> List[int]:
        """Optimize fee tier selection based on pool liquidity for concentrated liquidity.
        
        Queries fee tiers in order of expected liquidity with early exit once a tier
        with sufficient liquidity is found (avoids querying less common tiers).
        """
        fee_tiers = [3000, 10000, 500]  # Start with most common, try less common only if needed
        optimized_tiers = []
        
        try:
            # Early exit strategy: if a tier has good liquidity, prefer it
            min_liquidity_threshold = int(1e18)  # Configurable threshold
            
            for fee in fee_tiers:
                try:
                    pool_data = await asyncio.wait_for(
                        self._get_pool_liquidity(token0, token1, fee, chain_id, rpc_urls),
                        timeout=5.0
                    )
                    if isinstance(pool_data, dict) and pool_data.get("liquidity"):
                        optimized_tiers.append((fee, pool_data["liquidity"]))
                        # Early exit if liquidity is sufficient
                        if pool_data["liquidity"] >= min_liquidity_threshold:
                            break
                except asyncio.TimeoutError:
                    logger.debug(f"Fee tier {fee} query timeout, skipping")
                except Exception as e:
                    logger.debug(f"Fee tier {fee} query failed: {e}")
            
            # Sort by liquidity descending
            optimized_tiers.sort(key=lambda x: x[1], reverse=True)
            result = [tier[0] for tier in optimized_tiers]
            
            # Add missing tiers at end
            for fee in fee_tiers:
                if fee not in result:
                    result.append(fee)
            
            logger.debug(f"Optimized fee tier order for {token0}/{token1}: {result}")
            return result
            
        except Exception as e:
            logger.debug(f"Fee tier optimization failed, using default order: {e}")
            return fee_tiers

    async def _get_single_fee_quote(self, token_in: str, token_out: str, fee: int, amount_in: int, quoter: str, rpc_urls: List[str]) -> Dict[str, Any]:
        """Get quote for a single fee tier."""
        try:
            selector = function_signature_to_4byte_selector(
                "quoteExactInputSingle(address,address,uint24,uint256,uint160)"
            ).hex()
            
            encoded = abi_encode([
                "address", "address", "uint24", "uint256", "uint160"
            ], [token_in, token_out, fee, amount_in, 0]).hex()
            data = "0x" + selector + encoded
            
            # Try all RPCs for failover
            for rpc_url in rpc_urls:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": quoter, "data": data}, "latest"]
                }
                try:
                    result = await self._rpc_call(rpc_url, payload)
                    if result and result != "0x":
                        # QuoterV2 returns tuple: amountOut(uint256), sqrtPriceX96After(uint160), initializedTicksCrossed(int24), gasEstimate(uint32)
                        decoded = decode_abi(
                            ["uint256", "uint160", "int24", "uint32"],
                            bytes.fromhex(result[2:])
                        )
                        amount_out_wei, sqrt_price_x96_after, ticks_crossed, gas_estimate = decoded
                        
                        if amount_out_wei > 0:
                            return {
                                "amount_out_wei": amount_out_wei,
                                "sqrt_price_x96_after": sqrt_price_x96_after,
                                "ticks_crossed": ticks_crossed,
                                "gas_estimate": gas_estimate,
                            }
                except Exception:
                    continue
            
            return {"amount_out_wei": 0}
            
        except Exception as e:
            logger.debug(f"Single fee quote failed for fee {fee}: {e}")
            return {"amount_out_wei": 0}

    def _extract_revert_reason(self, error: Exception) -> Optional[str]:
        """Extract revert reason from RPC error."""
        try:
            if hasattr(error, "args") and len(error.args) > 0:
                err_msg = error.args[0]
                if isinstance(err_msg, dict) and "data" in err_msg:
                    data_hex = err_msg["data"]
                    if isinstance(data_hex, str) and len(data_hex) > 10:
                        try:
                            # Revert reason is ABI-encoded string after function selector
                            decoded = decode_abi(["string"], bytes.fromhex(data_hex[10:]))
                            return decoded[0]
                        except Exception:
                            return data_hex
                elif isinstance(err_msg, str):
                    return err_msg
            return None
        except Exception:
            return None

    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        to_chain_id: int = None,
    ) -> Dict[str, Any]:
        """Get swap quote from Uniswap V3 via QuoterV2 using JSON-RPC eth_call.
        - Uses config_manager for chain RPCs, token addresses, and protocol contracts
        - Tries fee tiers [500, 3000, 10000] and selects the best output
        """
        try:
            if not self.is_supported(chain_id):
                raise ValueError(f"Chain {chain_id} not supported by Uniswap adapter")

            if to_chain_id is not None and to_chain_id != chain_id:
                raise ValueError("Uniswap only supports same-chain swaps")

            # Resolve from/to token addresses via config manager (single source of truth)
            from app.core.config_manager import config_manager
            from ..core.errors import ProtocolError
            token_from_cfg = await config_manager.get_token_by_symbol(from_token.symbol)
            token_to_cfg = await config_manager.get_token_by_symbol(to_token.symbol)
            if not token_from_cfg or not token_to_cfg:
                raise ProtocolError(
                    message="Token config missing",
                    protocol="uniswap",
                    user_message=f"Unsupported token(s): {from_token.symbol}/{to_token.symbol}",
                )
            from_address = token_from_cfg.addresses.get(chain_id)
            to_address = token_to_cfg.addresses.get(chain_id)
            if not from_address or not to_address:
                raise ProtocolError(
                    message="Token not available on this chain",
                    protocol="uniswap",
                    user_message=f"Tokens not supported on chain {chain_id}",
                )

            # Resolve protocol and chain config
            uni_cfg = await config_manager.get_protocol("uniswap")
            chain_cfg = await config_manager.get_chain(chain_id)
            if not uni_cfg or not chain_cfg or not chain_cfg.rpc_urls:
                raise ProtocolError(
                    message="Missing Uniswap or chain configuration",
                    protocol="uniswap",
                    user_message="Network configuration unavailable"
                )
            contracts = uni_cfg.contract_addresses.get(chain_id, {})
            quoter = contracts.get("quoter")
            router = contracts.get("router")
            if not quoter or not router:
                raise ProtocolError(
                    message="Uniswap contracts missing",
                    protocol="uniswap",
                    user_message="Uniswap not available on this chain"
                )

            # Amount to wei using actual decimals from config
            decimals = token_from_cfg.decimals
            amount_wei = int(Decimal(amount) * (Decimal(10) ** decimals))

            # JSON-RPC clients (failover)
            rpc_urls = list(chain_cfg.rpc_urls)
            client = await self._get_client()

            # Prepare call data for QuoterV2.quoteExactInputSingle(address,address,uint24,uint256,uint160)
            from eth_utils import function_signature_to_4byte_selector



            # Cache key
            cache_key = f"{chain_id}:{from_address}:{to_address}:{amount_wei}"
            cached = self._quote_cache.get(cache_key)
            import time
            now = int(time.time())
            if cached and (now - cached.get("ts", 0) <= self._quote_ttl_seconds):
                return cached["data"]

            # V3 Concentrated Liquidity Optimization: Order fee tiers by liquidity
            fee_tiers = await self._optimize_fee_tier_selection(from_address, to_address, chain_id, rpc_urls)
            best = None
            
            # Enhanced quoting with parallel processing for better performance
            quote_tasks = []
            for fee in fee_tiers:
                task = self._get_single_fee_quote(from_address, to_address, fee, amount_wei, quoter, rpc_urls)
                quote_tasks.append((fee, task))
            
            # Process quotes in parallel for better performance
            try:
                results = await asyncio.gather(*[task for _, task in quote_tasks], return_exceptions=True)
                
                for i, result in enumerate(results):
                    fee = quote_tasks[i][0]
                    if isinstance(result, dict) and result.get("amount_out_wei", 0) > 0:
                        if not best or result["amount_out_wei"] > best["amount_out_wei"]:
                            best = result
                            best["fee"] = fee
                            
            except Exception as e:
                logger.debug(f"Parallel quoting failed, falling back to sequential: {e}")
                # Fallback to sequential processing
                for fee in fee_tiers:
                    result = await self._get_single_fee_quote(from_address, to_address, fee, amount_wei, quoter, rpc_urls)
                    if result.get("amount_out_wei", 0) > 0:
                        if not best or result["amount_out_wei"] > best["amount_out_wei"]:
                            best = result
                            best["fee"] = fee

            if not best:
                raise ProtocolError(
                    message="No valid quote from Uniswap Quoter",
                    protocol="uniswap",
                    user_message="Unable to fetch quote right now. Please try again."
                )

            data = {
                "success": True,
                "protocol": "uniswap",
                "router_address": router,
                "quoter_address": quoter,
                "from_address": from_address,
                "to_address": to_address,
                "amount_in_wei": amount_wei,
                "amount_out_wei": best["amount_out_wei"],
                "selected_fee": best["fee"],
                "chain_id": chain_id,
                "wallet_address": wallet_address,
                "estimated_gas": str(best.get("gas_estimate", 200000)),
                # Diagnostic fields
                "sqrt_price_x96_after": best.get("sqrt_price_x96_after"),
                "ticks_crossed": best.get("ticks_crossed"),
                "gas_estimate": best.get("gas_estimate"),
            }
            self._quote_cache[cache_key] = {"ts": now, "data": data}
            return data

        except Exception as e:
            logger.exception(f"Error getting Uniswap quote: {e}")
            return {
                "success": False,
                "error": f"Failed to get Uniswap quote: {str(e)}",
                "protocol": "uniswap"
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        enable_permit2: bool = True,
    ) -> Dict[str, Any]:
        """Build exactInputSingle transaction with optional permit2 integration and enhanced simulation."""
        try:
            if not quote.get("success", False):
                raise ValueError("Invalid quote")

            from eth_utils import function_signature_to_4byte_selector, to_checksum_address
            from app.core.config_manager import config_manager

            # Params
            token_in = quote["from_address"]
            token_out = quote["to_address"]
            fee = quote.get("selected_fee", 3000)
            recipient = quote["wallet_address"]
            amount_in = int(quote["amount_in_wei"])

            # Configurable slippage buffer (default 5%)
            slippage = 0.05
            try:
                from app.core.config_manager import config_manager
                slippage_cfg = await config_manager.get_setting("slippage")
                if slippage_cfg is not None:
                    slippage = float(slippage_cfg)
            except Exception:
                pass
            amount_out_min = int(int(quote["amount_out_wei"]) * (1 - slippage))

            # Configurable deadline (default 30 minutes)
            deadline_seconds = 1800
            try:
                from app.core.config_manager import config_manager
                deadline_cfg = await config_manager.get_setting("deadline")
                if deadline_cfg is not None:
                    deadline_seconds = int(deadline_cfg)
            except Exception:
                pass
            deadline = int(time.time()) + deadline_seconds

            # Enhanced allowance handling with permit2 support
            allowance_target = quote["router_address"]  # Default to router
            permit2_data = None
            
            if enable_permit2:
                try:
                    # Check if permit2 is configured and available
                    permit2_address = self.permit2_handler.PERMIT2_ADDRESS
                    allowance_target = permit2_address
                    
                    # Create mock permit2 data structure for Uniswap (similar to 0x pattern)
                    # In production, this would come from a permit2-enabled quote endpoint
                    permit2_data = {
                        "eip712": {
                            "types": {
                                "EIP712Domain": [
                                    {"name": "name", "type": "string"},
                                    {"name": "chainId", "type": "uint256"},
                                    {"name": "verifyingContract", "type": "address"}
                                ],
                                "PermitSingle": [
                                    {"name": "details", "type": "PermitDetails"},
                                    {"name": "spender", "type": "address"},
                                    {"name": "sigDeadline", "type": "uint256"}
                                ],
                                "PermitDetails": [
                                    {"name": "token", "type": "address"},
                                    {"name": "amount", "type": "uint160"},
                                    {"name": "expiration", "type": "uint48"},
                                    {"name": "nonce", "type": "uint48"}
                                ]
                            },
                            "domain": {
                                "name": "Permit2",
                                "chainId": chain_id,
                                "verifyingContract": permit2_address
                            },
                            "message": {
                                "details": {
                                    "token": token_in,
                                    "amount": str(amount_in),
                                    "expiration": str(deadline),
                                    "nonce": "0"
                                },
                                "spender": quote["router_address"],
                                "sigDeadline": str(deadline)
                            },
                            "primaryType": "PermitSingle"
                        }
                    }
                    logger.debug("Permit2 integration enabled for Uniswap transaction")
                except Exception as e:
                    logger.debug(f"Permit2 setup failed, using standard allowance: {e}")
                    enable_permit2 = False

            sqrt_price_limit = 0

            # Encode exactInputSingle(ExactInputSingleParams)
            selector = function_signature_to_4byte_selector(
                "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))"
            ).hex()
            params_tuple = (
                to_checksum_address(token_in),
                to_checksum_address(token_out),
                fee,
                to_checksum_address(recipient),
                0,  # deadline filled in contract or use block timestamp; we'll pass 0 to mean now
                amount_in,
                amount_out_min,
                sqrt_price_limit,
            )
            encoded = abi_encode([
                "(address,address,uint24,address,uint256,uint256,uint256,uint160)"
            ], [params_tuple]).hex()
            data = "0x" + selector + encoded

            # Enhanced gas estimation with multi-RPC failover
            chain_cfg = await config_manager.get_chain(chain_id)
            if not chain_cfg or not chain_cfg.rpc_urls:
                return {"error": "Missing RPC configuration"}
            
            gas_limit = None
            simulation_success = False
            
            # Prepare estimation tasks for all RPCs in parallel
            async def try_gas_estimation(rpc_url: str) -> Optional[int]:
                """Try gas estimation on single RPC."""
                try:
                    estimate_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_estimateGas",
                        "params": [
                            {
                                "from": recipient,
                                "to": quote["router_address"],
                                "data": data,
                                "value": "0x0"
                            }
                        ]
                    }
                    
                    gas_estimate = await self._rpc_call(rpc_url, estimate_payload, timeout=10.0)
                    if gas_estimate:
                        return int(gas_estimate, 16)
                except Exception as e:
                    logger.debug(f"Gas estimation failed on {rpc_url}: {e}")
                
                # Fallback: try eth_call simulation
                try:
                    call_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_call",
                        "params": [
                            {
                                "to": quote["router_address"],
                                "data": data,
                                "from": recipient,
                                "value": "0x0"
                            },
                            "latest"
                        ]
                    }
                    
                    await self._rpc_call(rpc_url, call_payload, timeout=10.0)
                    # Simulation succeeded, return default estimate
                    return int(quote.get("estimated_gas", "200000"))
                    
                except Exception as sim_err:
                    revert_reason = self._extract_revert_reason(sim_err)
                    logger.debug(f"Simulation failed on {rpc_url}: {revert_reason or str(sim_err)}")
                
                return None
            
            # Try all RPCs in parallel, return first successful result
            if chain_cfg.rpc_urls:
                results = await asyncio.gather(
                    *[try_gas_estimation(rpc) for rpc in chain_cfg.rpc_urls],
                    return_exceptions=False
                )
                # Use first successful result
                for result in results:
                    if result is not None:
                        gas_limit = result
                        simulation_success = True
                        logger.debug(f"Gas estimation successful: {gas_limit}")
                        break
            
            # If all RPCs failed, return detailed error
            if not simulation_success:
                return {
                    "error": "Transaction simulation failed on all RPCs",
                    "technical_details": "Unable to estimate gas or simulate transaction",
                    "user_message": "Unable to prepare transaction. Please try again or check token balances.",
                }

            # Build final transaction response
            transaction_data = {
                "to": quote["router_address"],
                "data": data,
                "value": "0",
                "gasLimit": hex(gas_limit) if gas_limit else quote.get("estimated_gas", "200000"),
                "chainId": chain_id
            }
            
            # Add permit2 information if enabled
            if enable_permit2 and permit2_data:
                transaction_data["permit2"] = {
                    "enabled": True,
                    "allowance_target": allowance_target,
                    "eip712_message": permit2_data["eip712"],
                    "requires_signature": True
                }
                logger.debug("Transaction prepared with permit2 support")
            else:
                transaction_data["permit2"] = {
                    "enabled": False,
                    "allowance_target": allowance_target,
                    "requires_approval": True
                }
            
            return transaction_data

        except Exception as e:
            logger.exception(f"Error building Uniswap transaction: {e}")
            return {
                "error": f"Failed to build transaction: {str(e)}",
                "technical_details": str(e)
            }

# Create instance
uniswap_adapter = UniswapAdapter()
