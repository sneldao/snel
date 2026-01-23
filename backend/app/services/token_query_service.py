"""
Unified service for token balance queries and transfer transaction building.
Follows ENHANCEMENT FIRST principle by using existing Web3Helper rather than
creating new balance/transfer-specific APIs.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.config.chains import CHAINS
from app.models.token import TokenInfo
from eth_abi.abi import encode as abi_encode
from web3 import Web3

logger = logging.getLogger(__name__)

# Cache for ENS resolutions to avoid redundant RPC calls
_ens_cache: dict[str, str | None] = {}


class TokenQueryService:
    """
    Unified service for token balance queries and transfer transaction building.

    Uses Web3 instances for each supported chain.
    Provides single source of truth for all token operations.
    """

    # ERC20 function selectors
    TRANSFER_SELECTOR = "0xa9059cbb"  # transfer(address to, uint256 amount)
    BALANCE_OF_SELECTOR = "0x70a08231"  # balanceOf(address account)

    def __init__(self) -> None:
        """Initialize service with Web3 instances."""
        # Use centralized chains configuration
        self.chain_names = {
            cid: cinfo.name.lower().replace(" ", "-") for cid, cinfo in CHAINS.items()
        }
        self.web3_instances: dict[int, Web3] = {}
        self._init_web3_instances()

        # Alchemy for token balance queries (from env)
        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY") or os.getenv("ALCHEMY_KEY")

    def _init_web3_instances(self) -> None:
        """Initialize Web3 instances for each supported chain."""
        for chain_id, chain_info in CHAINS.items():
            # Try specific env var first, then chain_info.rpc_url
            env_rpc = os.getenv(f"{chain_info.name.upper().replace(' ', '_')}_RPC_URL")
            rpc_url = env_rpc or chain_info.rpc_url

            if not rpc_url:
                # Fallback to the old naming convention
                legacy_name = self.chain_names.get(chain_id, "")
                rpc_url = os.getenv(f"{legacy_name.upper().replace('-', '_')}_RPC_URL")

            if rpc_url:
                try:
                    self.web3_instances[chain_id] = Web3(Web3.HTTPProvider(rpc_url))
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize Web3 for chain {chain_id}: {e}"
                    )

    async def _resolve_ens_web3bio(self, ens_name: str) -> str | None:
        """
        Fallback ENS resolution using Web3.bio API.

        Args:
            ens_name: ENS name or Ethereum address

        Returns:
            Checksum address or None if resolution fails
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"https://api.web3.bio/ns/{ens_name}"
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            address = data[0].get("address")
                            if address and Web3.is_address(address):
                                return Web3.to_checksum_address(address)
                        elif isinstance(data, dict):
                            address = data.get("address")
                            if address and Web3.is_address(address):
                                return Web3.to_checksum_address(address)
        except Exception as e:
            logger.debug(f"Web3.bio resolution failed for {ens_name}: {e}")

        return None

    async def _resolve_ens_ensdata(self, ens_name: str) -> str | None:
        """
        Fallback ENS resolution using ensdata.net API.

        Args:
            ens_name: ENS name or Ethereum address

        Returns:
            Checksum address or None if resolution fails
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"https://ensdata.net/{ens_name}"
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        address = data.get("address") or data.get("ethereum_address")
                        if address and Web3.is_address(address):
                            return Web3.to_checksum_address(address)
        except Exception as e:
            logger.debug(f"ensdata.net resolution failed for {ens_name}: {e}")

        return None

    async def resolve_address_async(
        self, address_or_ens: str, chain_id: int = 1
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Async version of resolve_address with multiple fallbacks.

        Args:
            address_or_ens: Ethereum address (0x...) or ENS name (name.eth)
            chain_id: Chain ID for context

        Returns:
            Tuple of (resolved_address, display_name)
        """
        # Try sync version first
        result = self.resolve_address(address_or_ens, chain_id)
        if result[0]:
            return result

        # If sync failed and it looks like ENS, try async fallbacks
        if address_or_ens.endswith(".eth"):
            # Try Web3.bio first
            web3bio_result = await self._resolve_ens_web3bio(address_or_ens)
            if web3bio_result:
                _ens_cache[address_or_ens] = web3bio_result
                logger.info(
                    f"Resolved ENS {address_or_ens} to {web3bio_result} via Web3.bio"
                )
                return web3bio_result, address_or_ens

            # Try ensdata.net as second fallback
            ensdata_result = await self._resolve_ens_ensdata(address_or_ens)
            if ensdata_result:
                _ens_cache[address_or_ens] = ensdata_result
                logger.info(
                    f"Resolved ENS {address_or_ens} to {ensdata_result} via ensdata.net"
                )
                return ensdata_result, address_or_ens

        return None, None

    def resolve_address(
        self, address_or_ens: str, chain_id: int = 1
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve an address or ENS name to a checksum address.

        Args:
            address_or_ens: Ethereum address (0x...) or ENS name (name.eth)
            chain_id: Chain ID for context

        Returns:
            Tuple of (resolved_address, display_name)
        """
        if not address_or_ens:
            return None, None

        # Check if it's already a valid address
        if Web3.is_address(address_or_ens):
            try:
                checksum_addr = Web3.to_checksum_address(address_or_ens)
                return checksum_addr, address_or_ens
            except Exception as e:
                logger.warning(f"Failed to checksum address {address_or_ens}: {e}")
                return None, None

        # Check if it looks like an ENS name
        if not address_or_ens.endswith(".eth"):
            return None, None

        # Try cache
        if address_or_ens in _ens_cache:
            cached_result = _ens_cache[address_or_ens]
            if cached_result:
                return cached_result, address_or_ens
            return None, None

        try:
            # Use mainnet (chain_id=1) for ENS resolution
            w3 = self.web3_instances.get(1)
            if not w3:
                logger.warning(
                    "No Web3 instance for mainnet (chain 1) - cannot resolve ENS"
                )
                return None, None

            # Resolve ENS to address
            resolved = w3.ens.address(address_or_ens)
            if resolved and resolved != "0x0000000000000000000000000000000000000000":
                checksum_addr = Web3.to_checksum_address(resolved)
                _ens_cache[address_or_ens] = checksum_addr
                logger.info(f"Resolved ENS {address_or_ens} to {checksum_addr}")
                return checksum_addr, address_or_ens

            logger.warning(f"ENS name {address_or_ens} resolved to zero address")
            _ens_cache[address_or_ens] = None
            return None, None

        except Exception as e:
            logger.warning(
                f"Failed to resolve ENS {address_or_ens} via Web3: {e}, trying fallbacks"
            )
            _ens_cache[address_or_ens] = None
            return None, None

    def is_valid_address(self, address: str) -> bool:
        """Check if a string is a valid Ethereum address (0x...)."""
        return Web3.is_address(address)

    async def get_mnee_transfers(
        self, wallet_address: str, chain_id: int, limit: int = 20
    ) -> dict[str, Any]:
        """
        Fetch MNEE transfer history via Alchemy Asset Transfers API.
        """
        try:
            if not self.alchemy_api_key:
                logger.warning(
                    "Alchemy API key not configured - cannot fetch transfers"
                )
                return {"transfers": [], "chain_id": chain_id, "source": "unavailable"}

            # Get MNEE token address for the chain
            from app.models.token import token_registry

            mnee = token_registry.get_token("mnee")
            if not mnee:
                logger.warning("MNEE token not found in registry")
                return {"transfers": [], "chain_id": chain_id, "source": "unavailable"}

            mnee_address = mnee.get_address(chain_id)
            if not mnee_address:
                logger.info(f"MNEE not supported on chain {chain_id}")
                return {"transfers": [], "chain_id": chain_id, "source": "unavailable"}

            # Map chain_id to Alchemy network name
            network_map = {
                1: "eth-mainnet",
                137: "polygon-mainnet",
                8453: "base-mainnet",
                42161: "arb-mainnet",
                10: "opt-mainnet",
            }

            network = network_map.get(chain_id)
            if not network:
                logger.warning(f"Alchemy not configured for chain {chain_id}")
                return {"transfers": [], "chain_id": chain_id, "source": "unavailable"}

            import aiohttp

            alchemy_url = f"https://{network}.g.alchemy.com/v2/{self.alchemy_api_key}"
            TRANSFER_TOPIC = (
                "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            )

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": mnee_address,
                        "topics": [
                            TRANSFER_TOPIC,
                            None,
                            f"0x{wallet_address.lower()[2:].zfill(64)}",
                        ],
                        "fromBlock": "0x0",
                        "toBlock": "latest",
                    }
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(alchemy_url, json=payload) as resp:
                    if resp.status != 200:
                        return {
                            "transfers": [],
                            "chain_id": chain_id,
                            "source": "error",
                        }

                    data = await resp.json()
                    if "error" in data:
                        return {
                            "transfers": [],
                            "chain_id": chain_id,
                            "source": "error",
                        }

                    logs = data.get("result", [])
                    transfers = []
                    for log in logs[-limit:]:
                        try:
                            from_addr = f"0x{log['topics'][1][-40:]}"
                            to_addr = f"0x{log['topics'][2][-40:]}"
                            amount_hex = log["data"]
                            amount_wei = int(amount_hex, 16)
                            amount = amount_wei / (10**mnee.decimals)

                            transfers.append(
                                {
                                    "from": from_addr,
                                    "to": to_addr,
                                    "amount": str(round(amount, 6)),
                                    "tx_hash": log.get("transactionHash", ""),
                                    "block_number": int(
                                        log.get("blockNumber", "0"), 16
                                    ),
                                    "timestamp": None,
                                }
                            )
                        except Exception:
                            continue

                    return {
                        "transfers": transfers,
                        "chain_id": chain_id,
                        "source": "alchemy",
                        "total": len(transfers),
                    }

        except Exception as e:
            logger.error(f"Failed to fetch MNEE transfers: {e}")
            return {"transfers": [], "chain_id": chain_id, "source": "error"}

    def estimate_gas(
        self, chain_id: int, transaction_type: str = "erc20_transfer"
    ) -> Dict[str, Any]:
        """
        Estimate gas for a transaction.
        """
        try:
            w3 = self.web3_instances.get(chain_id)
            if not w3 or not w3.is_connected():
                return {
                    "gas_limit": "100000"
                    if transaction_type == "erc20_transfer"
                    else "21000",
                    "gas_price_gwei": "0",
                    "estimated": False,
                }

            gas_price_wei = w3.eth.gas_price
            gas_price_gwei = float(w3.from_wei(gas_price_wei, "gwei"))

            gas_limits = {
                "erc20_transfer": 65000,
                "eth_transfer": 21000,
                "approval": 45000,
                "swap": 200000,
            }

            gas_limit = gas_limits.get(transaction_type, 100000)

            return {
                "gas_limit": str(gas_limit),
                "gas_price_gwei": str(round(gas_price_gwei, 2)),
                "estimated_cost_usd": "0",
                "estimated": True,
            }

        except Exception as e:
            logger.warning(f"Failed to estimate gas: {e}")
            return {"gas_limit": "100000", "gas_price_gwei": "0", "estimated": False}

    async def get_native_balance(
        self, wallet_address: str, chain_id: int
    ) -> float | None:
        """
        Get native token balance (ETH, MATIC, etc).
        """
        try:
            w3 = self.web3_instances.get(chain_id)
            if not w3 or not w3.is_connected():
                return None

            checksum_address = Web3.to_checksum_address(wallet_address)
            balance_wei = w3.eth.get_balance(checksum_address)
            balance_eth = float(w3.from_wei(balance_wei, "ether"))

            return balance_eth
        except Exception as e:
            logger.error(f"Failed to get native balance: {e}")
            return None

    async def get_token_balance(
        self, wallet_address: str, token_address: str, chain_id: int, decimals: int = 18
    ) -> Decimal | None:
        """
        Get ERC20 token balance via RPC call to balanceOf.
        """
        try:
            w3 = self.web3_instances.get(chain_id)
            if not w3 or not w3.is_connected():
                return None

            checksum_wallet = Web3.to_checksum_address(wallet_address)
            encoded_address = abi_encode(["address"], [checksum_wallet]).hex()
            data = self.BALANCE_OF_SELECTOR + encoded_address

            checksum_token = Web3.to_checksum_address(token_address)
            formatted_data = '0x' + data if not data.startswith('0x') else data
            result = w3.eth.call({
                'to': checksum_token,
                'data': formatted_data
            })

            balance_wei = int.from_bytes(result, "big")
            balance = Decimal(balance_wei) / Decimal(10**decimals)

            return balance
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return None

    async def get_balances(
        self,
        wallet_address: str,
        chain_id: int,
        tokens: list[TokenInfo] | None = None,
    ) -> dict[str, Any]:
        """
        Get native and token balances in one call.
        """
        result: dict[str, Any] = {
            "native_balance": await self.get_native_balance(wallet_address, chain_id),
            "token_balances": {},
        }

        if not tokens:
            from app.config.tokens import COMMON_TOKENS

            chain_tokens = COMMON_TOKENS.get(chain_id, {})
            for symbol, token_info in chain_tokens.items():
                try:
                    balance = await self.get_token_balance(
                        wallet_address,
                        token_info["address"],
                        chain_id,
                        token_info["decimals"],
                    )
                    if balance is not None:
                        result["token_balances"][symbol.upper()] = float(balance)
                except Exception:
                    continue
        else:
            for token in tokens:
                token_address = token.get_address(chain_id)
                if token_address:
                    balance = await self.get_token_balance(
                        wallet_address, token_address, chain_id, token.decimals
                    )
                    if balance is not None:
                        result["token_balances"][token.symbol] = float(balance)

        return result

    def build_transfer_transaction(
        self,
        token_address: str,
        to_address: str,
        amount: Decimal,
        decimals: int = 18,
        chain_id: int = 1,
    ) -> dict[str, Any]:
        """
        Build an ERC20 transfer transaction.
        """
        try:
            amount_wei = int(amount * Decimal(10**decimals))
            checksum_to = Web3.to_checksum_address(to_address)
            encoded_params = abi_encode(
                ["address", "uint256"], [checksum_to, amount_wei]
            )
            transfer_data = self.TRANSFER_SELECTOR + encoded_params.hex()

            transaction = {
                "to": Web3.to_checksum_address(token_address),
                "data": transfer_data,
                "value": 0,
            }
            return transaction
        except Exception as e:
            logger.error(f"Failed to build transfer transaction: {e}")
            raise ValueError(f"Could not build transfer transaction: {str(e)}")

    def validate_transfer(
        self, wallet_address: str, token_address: str, to_address: str, amount: Decimal
    ) -> tuple[bool, str | None]:
        """
        Validate transfer parameters.
        """
        if not Web3.is_address(wallet_address):
            return False, f"Invalid sender address: {wallet_address}"
        if not Web3.is_address(token_address):
            return False, f"Invalid token address: {token_address}"
        if not Web3.is_address(to_address):
            return False, f"Invalid recipient address: {to_address}"
        if amount <= 0:
            return False, "Amount must be greater than 0"
        if Web3.to_checksum_address(wallet_address) == Web3.to_checksum_address(
            to_address
        ):
            return False, "Cannot transfer to your own address"

        return True, None


token_query_service = TokenQueryService()
