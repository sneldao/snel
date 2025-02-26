import logging
import time
from typing import Dict, Any, Optional, Union, List, Tuple, Callable
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.exceptions import ContractLogicError
import json
from decimal import Decimal
from eth_utils import to_checksum_address, to_wei, from_wei
import os
from app.models.commands import SwapCommand

logger = logging.getLogger(__name__)

# Chain RPC URLs using environment variables
RPC_URLS = {
    1: os.environ.get("ETH_RPC_URL", f"https://eth-mainnet.g.alchemy.com/v2/{os.environ.get('ALCHEMY_KEY', '')}"),
    10: os.environ.get("OPTIMISM_RPC_URL", f"https://opt-mainnet.g.alchemy.com/v2/{os.environ.get('ALCHEMY_KEY', '')}"),
    137: os.environ.get("POLYGON_RPC_URL", f"https://polygon-mainnet.g.alchemy.com/v2/{os.environ.get('ALCHEMY_KEY', '')}"),
    42161: os.environ.get("ARBITRUM_RPC_URL", f"https://arb-mainnet.g.alchemy.com/v2/{os.environ.get('ALCHEMY_KEY', '')}"),
    8453: os.environ.get("BASE_RPC_URL", os.environ.get("QUICKNODE_ENDPOINT", "")),
    534352: os.environ.get("SCROLL_RPC_URL", "https://rpc.scroll.io"),
}

# Check if RPC URLs are configured
for chain_id, url in RPC_URLS.items():
    if not url or "your-key" in url:
        logger.warning(f"RPC URL for chain {chain_id} is not properly configured!")

# Default gas limits for different transaction types
DEFAULT_GAS_LIMITS = {
    "swap": 350000,  # Higher default for swaps
    "transfer": 100000,  # Standard ERC20 transfer
    "approve": 60000,  # Standard ERC20 approve
}

# Special tokens that require extra gas or have custom mechanics
SPECIAL_TOKENS = {
    "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dc7cc": {
        "name": "NURI",
        "chain_id": 534352,
        "gas_multiplier": 1.5,
        "warning": "NURI token has custom transfer mechanics that may require higher gas limits.",
        "suggestion": "Try using a smaller amount for NURI token swaps."
    }
}

# Lowercase version of special tokens for easier lookup
SPECIAL_TOKENS_LOWER = {k.lower(): v for k, v in SPECIAL_TOKENS.items()}

class TransactionExecutor:
    """
    Handles execution of blockchain transactions.
    
    This class provides methods for building, estimating gas, and executing
    transactions on various EVM chains.
    """
    
    def __init__(self):
        """Initialize the transaction executor."""
        self.web3_providers = {}
    
    def get_web3(self, chain_id: int) -> Web3:
        """
        Get a Web3 instance for the specified chain.
        
        Args:
            chain_id: The chain ID
            
        Returns:
            Web3 instance
            
        Raises:
            ValueError: If the chain ID is not supported
        """
        if chain_id not in self.web3_providers:
            if chain_id not in RPC_URLS:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            
            provider_url = RPC_URLS[chain_id]
            if not provider_url:
                raise ValueError(f"No provider URL configured for chain {chain_id}")
                
            logger.info(f"Creating Web3 provider for chain {chain_id} with URL: {provider_url[:20]}...")
            self.web3_providers[chain_id] = Web3(Web3.HTTPProvider(provider_url))
            
        return self.web3_providers[chain_id]
    
    async def estimate_gas_with_buffer(
        self, 
        web3: Web3, 
        tx: Dict[str, Any], 
        tx_type: str = "swap",
        token_address: Optional[str] = None
    ) -> int:
        """
        Estimate gas with fallback and safety buffer.
        
        Args:
            web3: Web3 instance
            tx: Transaction dict
            tx_type: Type of transaction (swap, transfer, approve)
            token_address: Optional token address for special token handling
            
        Returns:
            Estimated gas limit with safety buffer
        """
        try:
            logger.info(f"Estimating gas for transaction to {tx.get('to', 'unknown')} of type {tx_type}")
            # Try standard gas estimation
            estimated_gas = web3.eth.estimate_gas(tx)
            
            # Add 30% buffer for safety
            gas_with_buffer = int(estimated_gas * 1.3)
            
            # For known special tokens, add extra buffer
            if token_address and token_address.lower() in SPECIAL_TOKENS_LOWER:
                token_info = SPECIAL_TOKENS_LOWER[token_address.lower()]
                gas_with_buffer = int(gas_with_buffer * token_info.get("gas_multiplier", 1.5))
                logger.info(f"Adding extra gas buffer for special token {token_info['name']}")
            
            logger.info(f"Gas estimation successful. Base: {estimated_gas}, With buffer: {gas_with_buffer}")
            return gas_with_buffer
        
        except Exception as e:
            logger.warning(f"Gas estimation failed: {str(e)}. Using default gas limit for {tx_type}")
            
            # Use default gas limit based on transaction type
            default_gas = DEFAULT_GAS_LIMITS.get(tx_type, 250000)
            
            # For known special tokens, add extra buffer
            if token_address and token_address.lower() in SPECIAL_TOKENS_LOWER:
                token_info = SPECIAL_TOKENS_LOWER[token_address.lower()]
                default_gas = int(default_gas * token_info.get("gas_multiplier", 1.5))
                logger.info(f"Using higher default gas for special token {token_info['name']}")
            
            logger.info(f"Using default gas limit: {default_gas}")
            return default_gas
    
    async def get_gas_parameters(
        self, 
        web3: Web3, 
        chain_id: int,
        tx_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get appropriate gas parameters based on the chain.
        
        Args:
            web3: Web3 instance
            chain_id: Chain ID
            tx_data: Optional transaction data with gas parameters
            
        Returns:
            Dictionary with gas parameters
        """
        gas_params = {}
        
        try:
            # Handle gas price parameters for different chains
            if chain_id in [1, 137]:  # Ethereum, Polygon
                if tx_data and "gas_price" in tx_data:
                    gas_price = tx_data["gas_price"]
                    if isinstance(gas_price, str) and gas_price.startswith("0x"):
                        gas_price = int(gas_price, 16)
                    gas_params["gasPrice"] = gas_price
                    logger.info(f"Using provided gas price: {gas_price}")
                else:
                    # Get current gas price with 10% buffer
                    gas_price = web3.eth.gas_price
                    gas_params["gasPrice"] = int(gas_price * 1.1)
                    logger.info(f"Using network gas price with buffer: {gas_params['gasPrice']}")
                    
            else:  # EIP-1559 chains
                if tx_data and "max_fee_per_gas" in tx_data and "max_priority_fee_per_gas" in tx_data:
                    max_fee = tx_data["max_fee_per_gas"]
                    max_priority_fee = tx_data["max_priority_fee_per_gas"]
                    
                    if isinstance(max_fee, str) and max_fee.startswith("0x"):
                        max_fee = int(max_fee, 16)
                    if isinstance(max_priority_fee, str) and max_priority_fee.startswith("0x"):
                        max_priority_fee = int(max_priority_fee, 16)
                        
                    gas_params["maxFeePerGas"] = max_fee
                    gas_params["maxPriorityFeePerGas"] = max_priority_fee
                    logger.info(f"Using provided EIP-1559 gas params: maxFee={max_fee}, maxPriorityFee={max_priority_fee}")
                else:
                    try:
                        # Get fee data from the network
                        fee_data = web3.eth.fee_history(1, 'latest', [50])
                        base_fee = fee_data["baseFeePerGas"][-1]
                        
                        # Set max fee and priority fee
                        priority_fee = web3.eth.max_priority_fee
                        gas_params["maxFeePerGas"] = base_fee * 2 + priority_fee
                        gas_params["maxPriorityFeePerGas"] = priority_fee
                        logger.info(f"Using network EIP-1559 gas params: maxFee={gas_params['maxFeePerGas']}, maxPriorityFee={priority_fee}")
                    except Exception as e:
                        logger.warning(f"Failed to get EIP-1559 fee data: {e}. Falling back to legacy gas price.")
                        gas_price = web3.eth.gas_price
                        gas_params["gasPrice"] = int(gas_price * 1.1)
                        logger.info(f"Fallback to legacy gas price: {gas_params['gasPrice']}")
            
            return gas_params
        except Exception as e:
            logger.error(f"Error getting gas parameters: {e}")
            # Default to a reasonable gasPrice as fallback
            return {"gasPrice": web3.to_wei(30, 'gwei')}
    
    async def execute_transaction(
        self,
        wallet_address: str,
        tx_data: Dict[str, Any],
        chain_id: int,
        private_key: Optional[str] = None
    ) -> str:
        """
        Execute a transaction on the blockchain.
        
        Args:
            wallet_address: The wallet address to send the transaction from
            tx_data: The transaction data
            chain_id: The chain ID
            private_key: The private key to sign the transaction with
            
        Returns:
            The transaction hash
            
        Raises:
            ValueError: If the transaction fails
        """
        logger.info(f"Executing transaction on chain {chain_id} to {tx_data.get('to', 'unknown')}")
        
        # For testing purposes, if no private key is provided, return a mock transaction hash
        if not private_key:
            import hashlib
            mock_hash = hashlib.sha256(f"{time.time()}-{tx_data.get('to')}-{tx_data.get('value')}".encode()).hexdigest()
            tx_hash = f"0x{mock_hash}"
            logger.info(f"No private key provided, returning mock transaction hash: {tx_hash}")
            return tx_hash
        
        try:
            # Get Web3 instance
            web3 = self.get_web3(chain_id)
            
            # Create account from private key
            account: LocalAccount = Account.from_key(private_key)
            
            # Ensure wallet address matches account address
            if account.address.lower() != wallet_address.lower():
                error_msg = "Private key does not match wallet address"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Prepare transaction
            tx = {
                "from": wallet_address,
                "to": tx_data["to"],
                "data": tx_data["data"],
                "chainId": chain_id,
                "nonce": web3.eth.get_transaction_count(wallet_address),
            }
            
            # Determine transaction type
            tx_type = tx_data.get("method", "swap")
            
            # Handle gas parameters
            if "gas_limit" in tx_data:
                gas_limit = tx_data["gas_limit"]
                if isinstance(gas_limit, str):
                    if gas_limit.startswith("0x"):
                        gas_limit = int(gas_limit, 16)
                    else:
                        gas_limit = int(gas_limit)
                tx["gas"] = gas_limit
                logger.info(f"Using provided gas limit: {gas_limit}")
            else:
                # Use our improved gas estimation function
                token_address = tx_data.get("token_in_address") or tx_data.get("token_to_approve")
                tx["gas"] = await self.estimate_gas_with_buffer(
                    web3=web3, 
                    tx=tx, 
                    tx_type=tx_type,
                    token_address=token_address
                )
            
            # Get gas parameters (gasPrice or maxFeePerGas/maxPriorityFeePerGas)
            gas_params = await self.get_gas_parameters(web3, chain_id, tx_data)
            tx.update(gas_params)
            
            # Handle value field for native token transactions
            if "value" in tx_data and tx_data["value"]:
                # Ensure value is in the correct format
                value = tx_data["value"]
                if isinstance(value, str):
                    if value.startswith("0x"):
                        value = int(value, 16)
                    else:
                        value = int(value)
                tx["value"] = value
                logger.info(f"Transaction includes value: {value}")
            else:
                tx["value"] = 0
            
            # Log transaction details
            logger.info(f"Transaction details: {json.dumps({k: str(v) for k, v in tx.items()})}")
            
            # Sign transaction
            signed_tx = account.sign_transaction(tx)
            
            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"Transaction sent successfully! Hash: {tx_hash_hex}")
            
            # Return transaction hash
            return tx_hash_hex
        
        except ContractLogicError as e:
            error_msg = str(e).lower()
            logger.error(f"Contract logic error: {error_msg}")
            
            if "insufficient allowance" in error_msg:
                raise ValueError("Token approval needed before swap")
            elif "transfer amount exceeds balance" in error_msg:
                raise ValueError("Insufficient token balance")
            elif "price impact too high" in error_msg:
                raise ValueError("Price impact too high. Try a smaller amount or different token pair")
            else:
                raise ValueError(f"Transaction failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error executing transaction: {str(e)}")
            raise ValueError(f"Failed to execute transaction: {str(e)}")
    
    async def build_approval_transaction(
        self,
        token_address: str,
        spender_address: str,
        wallet_address: str,
        chain_id: int,
        amount: Optional[Union[int, str]] = None
    ) -> Dict[str, Any]:
        """
        Build a token approval transaction.
        
        Args:
            token_address: The token contract address
            spender_address: The address to approve (usually a router)
            wallet_address: The wallet address
            chain_id: The chain ID
            amount: The amount to approve (defaults to max uint256)
            
        Returns:
            Transaction data for the approval
        """
        # ERC20 approve function signature
        function_signature = "0x095ea7b3"
        
        # Default to max uint256 if no amount specified
        if amount is None:
            # Max uint256 value
            amount_hex = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        else:
            # Convert amount to hex
            if isinstance(amount, int):
                amount_hex = hex(amount)
            elif isinstance(amount, str) and amount.startswith("0x"):
                amount_hex = amount
            else:
                amount_hex = hex(int(amount))
        
        # Pad addresses to 32 bytes
        spender_address_padded = Web3.to_checksum_address(spender_address).lower().replace("0x", "").zfill(64)
        amount_padded = amount_hex.replace("0x", "").zfill(64)
        
        # Construct the data field
        data = f"{function_signature}{spender_address_padded}{amount_padded}"
        
        logger.info(f"Built approval transaction for token {token_address} with spender {spender_address}")
        
        return {
            "to": token_address,
            "data": data,
            "value": "0x0",
            "chain_id": chain_id,
            "method": "approve",
            "gas_limit": DEFAULT_GAS_LIMITS["approve"],
        }
    
    async def execute_swap(self, swap_command: SwapCommand, wallet_address: str, private_key: str, chain_id: int) -> Optional[str]:
        """
        Execute a swap transaction based on the swap command.
        This method is now properly part of the TransactionExecutor class.
        
        Args:
            swap_command: The swap command with details like token addresses and amounts
            wallet_address: The wallet address to execute the swap from
            private_key: The private key for signing the transaction
            chain_id: The chain ID to execute the swap on
            
        Returns:
            The transaction hash if successful, None otherwise
        """
        logger.info(f"Executing swap for {swap_command.amount_in} {swap_command.token_in} to {swap_command.token_out}")
        
        try:
            # Implementation needs to be added according to your specific requirements
            # This would interact with your chosen DEX aggregator or router
            
            # For now, we'll return None to indicate this needs implementation
            logger.warning("execute_swap method needs implementation specific to your chosen DEX integration")
            return None
            
        except Exception as e:
            logger.exception(f"Error executing swap: {e}")
            raise ValueError(f"Failed to execute swap: {str(e)}")

# Create a singleton instance
transaction_executor = TransactionExecutor()

# Convenience functions that use the TransactionExecutor
async def execute_transaction(
    wallet_address: str,
    tx_data: Dict[str, Any],
    chain_id: int,
    private_key: Optional[str] = None
) -> str:
    """
    Convenience function to execute a transaction.
    
    This uses the singleton TransactionExecutor instance.
    """
    return await transaction_executor.execute_transaction(
        wallet_address=wallet_address,
        tx_data=tx_data,
        chain_id=chain_id,
        private_key=private_key
    )

async def estimate_gas_with_buffer(
    web3: Web3, 
    tx: Dict[str, Any], 
    tx_type: str = "swap",
    token_address: Optional[str] = None
) -> int:
    """
    Convenience function to estimate gas with buffer.
    
    This uses the singleton TransactionExecutor instance.
    """
    return await transaction_executor.estimate_gas_with_buffer(
        web3=web3,
        tx=tx,
        tx_type=tx_type,
        token_address=token_address
    )

def get_web3(chain_id: int) -> Web3:
    """
    Convenience function to get a Web3 instance.
    
    This uses the singleton TransactionExecutor instance.
    """
    return transaction_executor.get_web3(chain_id)

# Remove the incorrectly defined function that was outside the class 