"""
Starknet service for interacting with Starknet nodes, fetching balances, and building transactions.
Uses starknet.py for low-level communication.
"""

from __future__ import annotations

import asyncio
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.client_models import Call
from starknet_py.net.full_node_client import FullNodeClient

from app.config.chains import CHAINS, ChainType
from app.config.tokens import COMMON_TOKENS

logger = logging.getLogger(__name__)


class StarknetService:
    """
    Service for Starknet-specific blockchain operations.
    """

    # Privacy contract addresses (placeholders for now)
    SHIELDED_TRANSFER_ADDR = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    PRIVATE_SWAP_ADDR = "0x0abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456"

    def __init__(self) -> None:
        """Initialize service with Starknet clients."""
        self.clients: dict[str | int, FullNodeClient] = {}
        self._init_clients()
        
        # Token metadata cache: {token_address: {"symbol": str, "decimals": int}}
        self._token_metadata_cache: dict[str, dict[str, Any]] = {}

    def _init_clients(self) -> None:
        """Initialize Starknet clients for each supported Starknet chain."""
        for chain_id, chain_info in CHAINS.items():
            if chain_info.type == ChainType.STARKNET:
                # Try specific env var first, then chain_info.rpc_url
                env_rpc = os.getenv(f"{chain_id.upper()}_RPC_URL")
                rpc_url = env_rpc or chain_info.rpc_url

                if rpc_url:
                    try:
                        self.clients[chain_id] = FullNodeClient(node_url=rpc_url)
                        logger.info(
                            f"Initialized Starknet client for {chain_id} with {rpc_url}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize Starknet client for chain {chain_id}: {e}"
                        )

    def get_client(self, chain_id: str | int = "SN_MAIN") -> FullNodeClient | None:
        """Get the Starknet client for a specific chain."""
        return self.clients.get(chain_id)

    async def get_native_balance(
        self, wallet_address: str, chain_id: str | int = "SN_MAIN"
    ) -> float:
        """
        Get native ETH balance on Starknet.
        
        Args:
            wallet_address: Starknet wallet address (hex)
            chain_id: Starknet chain identifier (SN_MAIN or SN_SEPOLIA)
            
        Returns:
            ETH balance as float
        """
        client = self.get_client(chain_id)
        if not client:
            return 0.0

        # ETH address on Starknet (same for Mainnet and Sepolia)
        eth_address = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"
        
        try:
            # Prepare call for balanceOf
            # Starknet addresses are felts (up to 251 bits), can be represented as int
            call = Call(
                to_addr=int(eth_address, 16),
                selector=get_selector_from_name("balanceOf"),
                calldata=[int(wallet_address, 16)]
            )
            
            result = await client.call_contract(call)
            
            # Result for balanceOf is usually a Uint256 (two u128 felts)
            if len(result) >= 2:
                balance_wei = result[0] + (result[1] << 128)
                return float(balance_wei) / 10**18
            elif len(result) == 1:
                # Older contracts might just return one felt
                return float(result[0]) / 10**18
                
            return 0.0
        except Exception as e:
            logger.error(f"Error getting native balance for {wallet_address} on {chain_id}: {e}")
            return 0.0

    async def get_token_metadata(
        self, token_address: str, chain_id: str | int = "SN_MAIN"
    ) -> dict[str, Any]:
        """
        Fetch token metadata (symbol, decimals) from contract.
        """
        cache_key = f"{chain_id}_{token_address.lower()}"
        if cache_key in self._token_metadata_cache:
            return self._token_metadata_cache[cache_key]
            
        client = self.get_client(chain_id)
        if not client:
            return {}
            
        try:
            # Use batch calls if possible, or individual calls
            # For simplicity here, individual calls
            addr_int = int(token_address, 16)
            
            # Decimals
            decimals_call = Call(
                to_addr=addr_int,
                selector=get_selector_from_name("decimals"),
                calldata=[]
            )
            decimals_res = await client.call_contract(decimals_call)
            decimals = decimals_res[0] if decimals_res else 18
            
            # Symbol - might be returned as felt (short string)
            symbol_call = Call(
                to_addr=addr_int,
                selector=get_selector_from_name("symbol"),
                calldata=[]
            )
            symbol_res = await client.call_contract(symbol_call)
            
            symbol = "UNKNOWN"
            if symbol_res:
                try:
                    # Convert felt to string if it's a short string
                    val = symbol_res[0]
                    # felt to bytes, then to string
                    symbol_bytes = val.to_bytes((val.bit_length() + 7) // 8, 'big')
                    symbol = symbol_bytes.decode('utf-8').strip('\x00')
                except Exception:
                    symbol = "TOKEN"

            metadata = {"symbol": symbol, "decimals": decimals}
            self._token_metadata_cache[cache_key] = metadata
            return metadata
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for token {token_address} on {chain_id}: {e}")
            return {"symbol": "UNKNOWN", "decimals": 18}

    async def get_token_balance(
        self, wallet_address: str, token_address: str, chain_id: str | int = "SN_MAIN"
    ) -> float:
        """
        Get ERC20-equivalent token balance on Starknet.
        """
        client = self.get_client(chain_id)
        if not client:
            return 0.0

        try:
            metadata = await self.get_token_metadata(token_address, chain_id)
            decimals = metadata.get("decimals", 18)
            
            call = Call(
                to_addr=int(token_address, 16),
                selector=get_selector_from_name("balanceOf"),
                calldata=[int(wallet_address, 16)]
            )
            result = await client.call_contract(call)
            
            if len(result) >= 2:
                balance_raw = result[0] + (result[1] << 128)
                return float(balance_raw) / 10**decimals
            elif len(result) == 1:
                return float(result[0]) / 10**decimals
                
            return 0.0
        except Exception as e:
            logger.error(f"Error getting token balance for {token_address} on {chain_id}: {e}")
            return 0.0

    async def get_balances(
        self, wallet_address: str, chain_id: str | int = "SN_MAIN"
    ) -> dict[str, float]:
        """
        Get all common token balances for a wallet on Starknet.
        """
        result = {}
        
        # Get native balance first
        result["ETH"] = await self.get_native_balance(wallet_address, chain_id)
        
        # Get other common tokens
        chain_tokens = COMMON_TOKENS.get(chain_id, {})
        for symbol, info in chain_tokens.items():
            if symbol.lower() == "eth":
                continue
            
            balance = await self.get_token_balance(wallet_address, info["address"], chain_id)
            result[symbol.upper()] = balance
            
        return result

    async def get_shielded_balance(
        self, wallet_address: str, token_symbol: str = "ETH", chain_id: str | int = "SN_MAIN"
    ) -> float:
        """
        Get shielded balance for a wallet on Starknet.
        Currently a placeholder using commitment queries.
        """
        client = self.get_client(chain_id)
        if not client:
            return 0.0
            
        try:
            # In a real ZK system, this would query commitments or a viewing key service
            # For hackathon demo, we query the shielded_transfer contract
            call = Call(
                to_addr=int(self.SHIELDED_TRANSFER_ADDR, 16),
                selector=get_selector_from_name("get_shielded_balance"),
                calldata=[int(wallet_address, 16), int(token_symbol.encode().hex(), 16)]
            )
            result = await client.call_contract(call)
            return float(result[0]) / 10**18 if result else 0.0
        except Exception as e:
            logger.debug(f"Failed to fetch shielded balance: {e}")
            return 0.0

    def build_shield_tx(
        self, token_address: str, amount: Decimal, commitment: str, decimals: int = 18
    ) -> dict[str, Any]:
        """
        Build transaction to shield assets on Starknet.
        """
        amount_raw = int(amount * Decimal(10**decimals))
        return {
            "contractAddress": self.SHIELDED_TRANSFER_ADDR,
            "entrypoint": "deposit",
            "calldata": [commitment, str(amount_raw), "0"],
            "type": "starknet_call",
            "metadata": {"action": "shield", "token": token_address}
        }

    def build_unshield_tx(
        self, nullifier: str, recipient: str, amount: Decimal, proof: List[str], decimals: int = 18
    ) -> dict[str, Any]:
        """
        Build transaction to unshield assets on Starknet.
        """
        amount_raw = int(amount * Decimal(10**decimals))
        return {
            "contractAddress": self.SHIELDED_TRANSFER_ADDR,
            "entrypoint": "withdraw",
            "calldata": [nullifier, recipient, str(amount_raw), "0", str(len(proof)), *proof],
            "type": "starknet_call",
            "metadata": {"action": "unshield"}
        }


# Singleton instance
starknet_service = StarknetService()
