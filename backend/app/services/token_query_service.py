"""
Token query service - Single source of truth for balance queries and transfer building.
Consolidates Web3Helper usage across balance and transfer processors.

Follows ENHANCEMENT FIRST principle by using existing Web3Helper rather than
creating new balance/transfer-specific APIs.
"""
import logging
import os
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from eth_abi import encode as abi_encode

from app.models.token import TokenInfo

logger = logging.getLogger(__name__)

# Cache for ENS resolutions to avoid repeated lookups
_ens_cache: Dict[str, Optional[str]] = {}


class TokenQueryService:
    """
    Unified service for token balance queries and transfer transaction building.
    
    Uses Web3Helper from portfolio_service for consistency (DRY principle).
    Provides single source of truth for all token operations.
    """
    
    # ERC20 function selectors
    TRANSFER_SELECTOR = "0xa9059cbb"  # transfer(address to, uint256 amount)
    BALANCE_OF_SELECTOR = "0x70a08231"  # balanceOf(address account)
    
    def __init__(self):
        """Initialize service with Web3 instances."""
        self.chain_names = {
            1: "eth-mainnet",
            8453: "base-mainnet",
            42161: "arb-mainnet",
            10: "opt-mainnet",
            137: "polygon-mainnet",
            43114: "avalanche-mainnet",
            56: "bsc-mainnet"
        }
        self.web3_instances: Dict[int, Web3] = {}
        self._init_web3_instances()
        
        # Alchemy for token balance queries (from env, same as portfolio service)
        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY") or os.getenv("ALCHEMY_KEY")
    
    def _init_web3_instances(self):
        """Initialize Web3 instances for each supported chain."""
        for chain_id, chain_name in self.chain_names.items():
            rpc_url = os.getenv(f"{chain_name.upper()}_RPC_URL")
            if rpc_url:
                try:
                    self.web3_instances[chain_id] = Web3(Web3.HTTPProvider(rpc_url))
                except Exception as e:
                    logger.warning(f"Failed to initialize Web3 for chain {chain_id}: {e}")
    
    async def _resolve_ens_web3bio(self, identity: str) -> Optional[str]:
        """
        Fallback ENS resolution using Web3.bio API.
        
        Args:
            identity: ENS name or Ethereum address
            
        Returns:
            Checksum address or None if resolution fails
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://api.web3.bio/ns/{identity}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            address = data[0].get('address')
                            if address and Web3.is_address(address):
                                return Web3.to_checksum_address(address)
                        elif isinstance(data, dict):
                            address = data.get('address')
                            if address and Web3.is_address(address):
                                return Web3.to_checksum_address(address)
        except Exception as e:
            logger.debug(f"Web3.bio resolution failed for {identity}: {e}")
        
        return None

    async def _resolve_ens_ensdata(self, identity: str) -> Optional[str]:
        """
        Fallback ENS resolution using ensdata.net API (free, no API key required).
        
        Args:
            identity: ENS name or Ethereum address
            
        Returns:
            Checksum address or None if resolution fails
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://ensdata.net/{identity}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # ensdata.net returns the address in different ways
                        address = data.get('address') or data.get('ethereum_address')
                        if address and Web3.is_address(address):
                            return Web3.to_checksum_address(address)
        except Exception as e:
            logger.debug(f"ensdata.net resolution failed for {identity}: {e}")
        
        return None

    async def resolve_address_async(self, address_or_ens: str, chain_id: int = 1) -> Tuple[Optional[str], Optional[str]]:
        """
        Async version of resolve_address with multiple fallbacks (Web3.bio, ensdata.net).
        
        Resolution order:
        1. Native Web3 resolution
        2. Web3.bio API
        3. ensdata.net API (free, no auth required)
        
        Args:
            address_or_ens: Ethereum address (0x...) or ENS name (name.eth)
            chain_id: Chain ID for context (ENS resolves on mainnet regardless)
            
        Returns:
            Tuple of (resolved_address, display_name)
        """
        # First try synchronous resolution
        result = self.resolve_address(address_or_ens, chain_id)
        if result[0]:
            return result
        
        # If sync failed and it looks like ENS, try async fallbacks
        if address_or_ens.endswith('.eth'):
            # Try Web3.bio first
            web3bio_result = await self._resolve_ens_web3bio(address_or_ens)
            if web3bio_result:
                _ens_cache[address_or_ens] = web3bio_result
                logger.info(f"Resolved ENS {address_or_ens} to {web3bio_result} via Web3.bio")
                return web3bio_result, address_or_ens
            
            # Try ensdata.net as second fallback
            ensdata_result = await self._resolve_ens_ensdata(address_or_ens)
            if ensdata_result:
                _ens_cache[address_or_ens] = ensdata_result
                logger.info(f"Resolved ENS {address_or_ens} to {ensdata_result} via ensdata.net")
                return ensdata_result, address_or_ens
        
        return None, None

    def resolve_address(self, address_or_ens: str, chain_id: int = 1) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve an address or ENS name to a checksum address.
        
        Handles both Ethereum addresses and ENS names.
        Uses Mainnet (chain_id=1) for ENS resolution with Web3.bio fallback.
        
        Args:
            address_or_ens: Ethereum address (0x...) or ENS name (name.eth)
            chain_id: Chain ID for context (ENS resolves on mainnet regardless)
            
        Returns:
            Tuple of (resolved_address, display_name) where:
            - resolved_address: Checksum Ethereum address or None if invalid
            - display_name: Original ENS name if input was ENS, else the address
        """
        if not address_or_ens:
            return None, None
        
        # Check if it's already a valid address
        if Web3.is_address(address_or_ens):
            try:
                checksum_addr = Web3.to_checksum_address(address_or_ens)
                return checksum_addr, checksum_addr
            except Exception as e:
                logger.warning(f"Failed to checksum address {address_or_ens}: {e}")
                return None, None
        
        # Check if it looks like an ENS name (word.eth pattern)
        if not address_or_ens.endswith('.eth'):
            return None, None
        
        # Try to resolve ENS
        if address_or_ens in _ens_cache:
            cached_result = _ens_cache[address_or_ens]
            if cached_result:
                return cached_result, address_or_ens
            return None, None
        
        try:
            # Use mainnet (chain_id=1) for ENS resolution
            w3 = self.web3_instances.get(1)
            if not w3:
                logger.warning("No Web3 instance for mainnet (chain 1) - cannot resolve ENS")
                return None, None
            
            # Resolve ENS to address
            resolved = w3.eth.name_to_address(address_or_ens)
            if resolved and resolved != "0x0000000000000000000000000000000000000000":
                checksum_addr = Web3.to_checksum_address(resolved)
                _ens_cache[address_or_ens] = checksum_addr
                logger.info(f"Resolved ENS {address_or_ens} to {checksum_addr}")
                return checksum_addr, address_or_ens
            
            logger.warning(f"ENS name {address_or_ens} resolved to zero address")
            _ens_cache[address_or_ens] = None
            return None, None
            
        except Exception as e:
            logger.warning(f"Failed to resolve ENS {address_or_ens} via Web3: {e}, trying Web3.bio fallback")
            # Will try async fallback in async context
            _ens_cache[address_or_ens] = None
            return None, None
    
    def is_valid_address(self, address: str) -> bool:
        """Check if a string is a valid Ethereum address (0x...)."""
        return Web3.is_address(address)
    
    async def get_mnee_transfers(
        self,
        wallet_address: str,
        chain_id: int,
        limit: int = 20
    ) -> Dict[str, any]:
        """
        Fetch MNEE transfer history via Alchemy Asset Transfers API.
        
        Source of truth: blockchain via Alchemy, not app database.
        Works across all chains where MNEE is deployed.
        
        Args:
            wallet_address: User's wallet address
            chain_id: Chain ID to query
            limit: Max transfers to return
            
        Returns:
            Dict with transfers list and metadata
        """
        try:
            if not self.alchemy_api_key:
                logger.warning("Alchemy API key not configured - cannot fetch transfers")
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
                8453: "base-mainnet",
                137: "polygon-mainnet",
                42161: "arb-mainnet",
                10: "opt-mainnet",
            }
            
            network = network_map.get(chain_id)
            if not network:
                logger.warning(f"Alchemy not configured for chain {chain_id}")
                return {"transfers": [], "chain_id": chain_id, "source": "unavailable"}
            
            # Use Alchemy API via requests
            import aiohttp
            
            alchemy_url = f"https://{network}.g.alchemy.com/v2/{self.alchemy_api_key}"
            
            # Query using eth_getLogs for Transfer events
            # Transfer event signature: keccak256("Transfer(address,address,uint256)")
            TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": mnee_address,
                        "topics": [
                            TRANSFER_TOPIC,
                            # Topic 1 (from): can be any address
                            None,
                            # Topic 2 (to): filter by wallet address
                            f"0x{wallet_address.lower()[2:].zfill(64)}"
                        ],
                        "fromBlock": "0x0",
                        "toBlock": "latest"
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(alchemy_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Alchemy API error: {resp.status}")
                        return {"transfers": [], "chain_id": chain_id, "source": "error"}
                    
                    data = await resp.json()
                    
                    if "error" in data:
                        logger.error(f"Alchemy RPC error: {data['error']}")
                        return {"transfers": [], "chain_id": chain_id, "source": "error"}
                    
                    logs = data.get("result", [])
                    
                    # Parse transfer events
                    transfers = []
                    for log in logs[-limit:]:  # Get last N transfers
                        try:
                            # Parse log data
                            from_addr = f"0x{log['topics'][1][-40:]}"  # Remove padding
                            to_addr = f"0x{log['topics'][2][-40:]}"
                            
                            # Decode amount from data field (256-bit uint)
                            amount_hex = log['data']
                            amount_wei = int(amount_hex, 16)
                            amount = amount_wei / (10 ** mnee.decimals)
                            
                            transfers.append({
                                "from": from_addr,
                                "to": to_addr,
                                "amount": str(round(amount, 6)),
                                "tx_hash": log.get("transactionHash", ""),
                                "block_number": int(log.get("blockNumber", "0"), 16),
                                "timestamp": None,  # Would need block timestamp lookup
                            })
                        except Exception as e:
                            logger.warning(f"Failed to parse transfer log: {e}")
                            continue
                    
                    logger.info(f"Fetched {len(transfers)} MNEE transfers for {wallet_address} on chain {chain_id}")
                    
                    return {
                        "transfers": transfers,
                        "chain_id": chain_id,
                        "source": "alchemy",
                        "total": len(transfers)
                    }
                    
        except Exception as e:
            logger.error(f"Failed to fetch MNEE transfers: {e}")
            return {"transfers": [], "chain_id": chain_id, "source": "error"}
    
    def estimate_gas(self, chain_id: int, transaction_type: str = "erc20_transfer") -> Dict[str, any]:
        """
        Estimate gas for a transaction.
        
        Returns gas limit and typical gas price for the chain.
        
        Args:
            chain_id: Chain ID
            transaction_type: Type of transaction (erc20_transfer, eth_transfer, etc.)
            
        Returns:
            Dict with gas_limit and gas_price_gwei
        """
        try:
            w3 = self.web3_instances.get(chain_id)
            if not w3 or not w3.is_connected():
                logger.warning(f"No Web3 connection for chain {chain_id}")
                return {
                    "gas_limit": "100000" if transaction_type == "erc20_transfer" else "21000",
                    "gas_price_gwei": "0",
                    "estimated": False
                }
            
            # Get current gas price
            gas_price_wei = w3.eth.gas_price
            gas_price_gwei = float(w3.from_wei(gas_price_wei, 'gwei'))
            
            # Standard gas estimates
            gas_limits = {
                "erc20_transfer": 65000,      # ERC20 transfer
                "eth_transfer": 21000,        # ETH transfer
                "approval": 45000,            # Token approval
                "swap": 200000,               # Complex swap
            }
            
            gas_limit = gas_limits.get(transaction_type, 100000)
            
            return {
                "gas_limit": str(gas_limit),
                "gas_price_gwei": str(round(gas_price_gwei, 2)),
                "estimated_cost_usd": "0",   # Would need price oracle
                "estimated": True
            }
            
        except Exception as e:
            logger.warning(f"Failed to estimate gas: {e}")
            return {
                "gas_limit": "100000",
                "gas_price_gwei": "0",
                "estimated": False
            }
    
    async def get_native_balance(self, wallet_address: str, chain_id: int) -> Optional[float]:
        """
        Get native token balance (ETH, MATIC, etc).
        
        Args:
            wallet_address: Wallet address to query
            chain_id: Chain ID
            
        Returns:
            Balance in native units (e.g., ETH), or None if failed
        """
        try:
            w3 = self.web3_instances.get(chain_id)
            if not w3:
                logger.warning(f"No Web3 instance for chain {chain_id}")
                return None
            
            balance_wei = w3.eth.get_balance(wallet_address)
            balance_eth = float(w3.from_wei(balance_wei, 'ether'))
            
            logger.debug(f"Native balance for {wallet_address} on chain {chain_id}: {balance_eth}")
            return balance_eth
            
        except Exception as e:
            logger.error(f"Failed to get native balance: {e}")
            return None
    
    async def get_token_balance(
        self,
        wallet_address: str,
        token_address: str,
        chain_id: int,
        decimals: int = 18
    ) -> Optional[Decimal]:
        """
        Get ERC20 token balance via RPC call to balanceOf.
        
        Args:
            wallet_address: Wallet address to query
            token_address: Token contract address
            chain_id: Chain ID
            decimals: Token decimal places
            
        Returns:
            Balance as Decimal, or None if failed
        """
        try:
            w3 = self.web3_instances.get(chain_id)
            if not w3:
                logger.warning(f"No Web3 instance for chain {chain_id}")
                return None
            
            # Encode balanceOf call
            encoded_address = abi_encode(['address'], [wallet_address]).hex()
            data = self.BALANCE_OF_SELECTOR + encoded_address
            
            # Call the contract
            result = w3.eth.call({
                'to': token_address,
                'data': data
            })
            
            # Decode result
            balance_wei = int.from_bytes(result, 'big')
            balance = Decimal(balance_wei) / Decimal(10 ** decimals)
            
            logger.debug(f"Token balance for {wallet_address} on chain {chain_id}: {balance}")
            return balance
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return None
    
    async def get_balances(
        self,
        wallet_address: str,
        chain_id: int,
        tokens: Optional[List[TokenInfo]] = None
    ) -> Dict[str, any]:
        """
        Get native and token balances in one call.
        
        Args:
            wallet_address: Wallet address
            chain_id: Chain ID
            tokens: Optional list of specific tokens to query
            
        Returns:
            Dict with native_balance and token_balances
        """
        result = {
            "native_balance": await self.get_native_balance(wallet_address, chain_id),
            "token_balances": {}
        }
        
        if tokens:
            for token in tokens:
                token_address = token.get_address(chain_id)
                if token_address:
                    balance = await self.get_token_balance(
                        wallet_address,
                        token_address,
                        chain_id,
                        token.decimals
                    )
                    result["token_balances"][token.symbol] = balance
        
        return result
    
    def build_transfer_transaction(
        self,
        token_address: str,
        to_address: str,
        amount: Decimal,
        decimals: int = 18,
        chain_id: int = 1
    ) -> Dict[str, str]:
        """
        Build an ERC20 transfer transaction.
        
        Single source of truth for transfer transaction building (DRY principle).
        
        Args:
            token_address: Token contract address
            to_address: Recipient address
            amount: Amount to transfer (as Decimal)
            decimals: Token decimal places
            chain_id: Chain ID
            
        Returns:
            Transaction dict {to, data, value, chainId}
        """
        try:
            # Convert amount to token units (wei)
            amount_wei = int(amount * Decimal(10 ** decimals))
            
            # DEBUG: Log the scaling
            logger.info(f"DEBUG build_transfer: amount={amount}, decimals={decimals}, amount_wei={amount_wei}")
            
            # Encode transfer(address to, uint256 amount)
            encoded_params = abi_encode(
                ['address', 'uint256'],
                [to_address, amount_wei]
            )
            transfer_data = self.TRANSFER_SELECTOR + encoded_params.hex()
            
            transaction = {
                "to": token_address,
                "data": transfer_data,
                "value": "0",
                "chainId": chain_id,
                "gasLimit": "100000"  # Conservative estimate for ERC20 transfer
            }
            
            logger.debug(f"Built transfer transaction: {amount} tokens to {to_address}")
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to build transfer transaction: {e}")
            raise ValueError(f"Could not build transfer transaction: {str(e)}")
    
    def validate_transfer(
        self,
        wallet_address: str,
        token_address: str,
        to_address: str,
        amount: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate transfer parameters before building transaction.
        
        Args:
            wallet_address: Sender address
            token_address: Token contract address
            to_address: Recipient address
            amount: Amount to transfer
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate addresses
        if not Web3.is_address(wallet_address):
            return False, f"Invalid sender address: {wallet_address}"
        
        if not Web3.is_address(token_address):
            return False, f"Invalid token address: {token_address}"
        
        if not Web3.is_address(to_address):
            return False, f"Invalid recipient address: {to_address}"
        
        # Validate amount
        if amount <= 0:
            return False, "Amount must be greater than 0"
        
        # Prevent self-transfer
        if Web3.to_checksum_address(wallet_address) == Web3.to_checksum_address(to_address):
            return False, "Cannot transfer to your own address"
        
        return True, None


# Singleton instance for use across processors
token_query_service = TokenQueryService()
