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
