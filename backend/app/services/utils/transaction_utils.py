"""
Shared transaction utilities - Single source of truth for transaction building.
Consolidates duplicate logic across services, processors, and adapters.
DRY principle: No more scattered approval encoding, step detection, or transaction data creation.
"""
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

from eth_abi import encode as abi_encode
from app.models.unified_models import TransactionData

logger = logging.getLogger(__name__)


class TransactionUtils:
    """Centralized transaction utility functions - shared across all services."""
    
    # Standard ERC20 function selector for approve(address spender, uint256 amount)
    ERC20_APPROVE_SELECTOR = "0x095ea7b3"
    
    # Standard token swap function selector (0x DEX)
    SWAP_SELECTOR = "0x2213bc0b"
    
    # Circle CCTP bridge selector
    CIRCLE_BRIDGE_SELECTOR = "0x12e4d8d1"
    
    @staticmethod
    def encode_erc20_approval(spender: str, amount: Decimal) -> str:
        """
        Encode ERC20 approve function call.
        Single source of truth for approval encoding.
        
        Function signature: approve(address spender, uint256 amount)
        
        Args:
            spender: Address authorized to spend the tokens
            amount: Amount to approve (as Decimal, will be converted to wei)
            
        Returns:
            Encoded function call with selector + parameters
        """
        try:
            # Convert amount to wei (assuming 18 decimals for standard ERC20)
            amount_wei = int(amount * 10**18)
            
            # Encode the function call: 0x095ea7b3 + abi.encode(address, uint256)
            encoded_params = abi_encode(['address', 'uint256'], [spender, amount_wei])
            return TransactionUtils.ERC20_APPROVE_SELECTOR + encoded_params.hex()
            
        except Exception as e:
            logger.error(f"Failed to encode approval: {e}")
            raise ValueError(f"Could not encode ERC20 approval: {str(e)}")
    
    @staticmethod
    def encode_erc20_approval_with_decimals(
        spender: str,
        amount: Decimal,
        decimals: int = 18
    ) -> str:
        """
        Encode ERC20 approval with custom token decimals.
        
        Args:
            spender: Address authorized to spend tokens
            amount: Amount to approve
            decimals: Token decimal places (default 18)
            
        Returns:
            Encoded function call
        """
        try:
            amount_wei = int(amount * (10**decimals))
            encoded_params = abi_encode(['address', 'uint256'], [spender, amount_wei])
            return TransactionUtils.ERC20_APPROVE_SELECTOR + encoded_params.hex()
            
        except Exception as e:
            logger.error(f"Failed to encode approval with decimals: {e}")
            raise ValueError(f"Could not encode ERC20 approval: {str(e)}")
    
    @staticmethod
    def detect_approval_transaction(data: str) -> bool:
        """
        Detect if a transaction is an ERC20 approval.
        Single source of truth - no more duplicated detection logic.
        
        Args:
            data: Transaction data (hex string)
            
        Returns:
            True if this is an approval transaction, False otherwise
        """
        if not data or len(data) < 10:
            return False
        
        # Check if function selector matches ERC20 approve
        return data[:10].lower() == TransactionUtils.ERC20_APPROVE_SELECTOR.lower()
    
    @staticmethod
    def detect_swap_transaction(data: str) -> bool:
        """
        Detect if a transaction is a swap/exchange.
        
        Args:
            data: Transaction data (hex string)
            
        Returns:
            True if this looks like a swap transaction
        """
        if not data or len(data) < 10:
            return False
        
        selector = data[:10].lower()
        # Common DEX swap selectors
        swap_selectors = {
            TransactionUtils.SWAP_SELECTOR.lower(),
            "0x3593cde5",  # Uniswap V3 multicall
            "0xac9b441f",  # Uniswap V2 swap exact tokens
            "0x8803dbee",  # Uniswap V2 swap tokens for exact
        }
        
        return selector in swap_selectors
    
    @staticmethod
    def detect_bridge_transaction(data: str) -> bool:
        """
        Detect if a transaction is a bridge operation.
        
        Args:
            data: Transaction data (hex string)
            
        Returns:
            True if this looks like a bridge transaction
        """
        if not data or len(data) < 10:
            return False
        
        selector = data[:10].lower()
        # Common bridge selectors
        bridge_selectors = {
            TransactionUtils.CIRCLE_BRIDGE_SELECTOR.lower(),
            "0x9992dc15",  # Axelar gateway send
            "0xd8d4e4c8",  # Stargate bridge
        }
        
        return selector in bridge_selectors
    
    @staticmethod
    def detect_step_type(data: str) -> Optional[str]:
        """
        Detect the type of transaction step.
        Single source of truth for step type detection.
        
        Args:
            data: Transaction data (hex string)
            
        Returns:
            'approval', 'swap', 'bridge', or None if unknown
        """
        if TransactionUtils.detect_approval_transaction(data):
            return "approval"
        elif TransactionUtils.detect_swap_transaction(data):
            return "swap"
        elif TransactionUtils.detect_bridge_transaction(data):
            return "bridge"
        
        return None
    
    @staticmethod
    def create_transaction_data(
        result: Dict[str, Any],
        chain_id: int,
        from_address: Optional[str] = None
    ) -> Optional[TransactionData]:
        """
        Create TransactionData from API response.
        Single source of truth for transaction data creation.
        
        Handles multiple response formats:
        - Direct transaction format: {to, data, value, gasLimit}
        - Nested transaction format: {transaction: {to, data, ...}}
        - Multi-step format: {steps: [{to, data, ...}]}
        
        Args:
            result: API response containing transaction data
            chain_id: Target chain ID
            from_address: Optional sender address
            
        Returns:
            TransactionData object or None if no transaction data found
        """
        if not result or not isinstance(result, dict):
            return None
        
        # Try direct transaction format first
        if "to" in result:
            return TransactionData(
                to=result.get("to", ""),
                data=result.get("data", "0x"),
                value=str(result.get("value", "0")),
                gasLimit=str(result.get("gasLimit", result.get("gas_limit", ""))),
                chainId=chain_id,
                from_address=from_address or result.get("from")
            )
        
        # Try nested transaction format
        if "transaction" in result:
            tx = result["transaction"]
            if isinstance(tx, dict):
                # Handle doubly-nested format
                if "transaction" in tx:
                    actual_tx = tx["transaction"]
                    return TransactionData(
                        to=actual_tx.get("to", ""),
                        data=actual_tx.get("data", "0x"),
                        value=str(actual_tx.get("value", "0")),
                        gasLimit=str(actual_tx.get("gas_limit", actual_tx.get("gasLimit", ""))),
                        chainId=chain_id,
                        from_address=from_address or actual_tx.get("from")
                    )
                else:
                    return TransactionData(
                        to=tx.get("to", ""),
                        data=tx.get("data", "0x"),
                        value=str(tx.get("value", "0")),
                        gasLimit=str(tx.get("gas_limit", tx.get("gasLimit", ""))),
                        chainId=chain_id,
                        from_address=from_address or tx.get("from")
                    )
        
        # Try multi-step format
        if "steps" in result and result["steps"]:
            first_step = result["steps"][0]
            return TransactionData(
                to=first_step.get("to", ""),
                data=first_step.get("data", "0x"),
                value=str(first_step.get("value", "0")),
                gasLimit=str(first_step.get("gasLimit", first_step.get("gas_limit", ""))),
                chainId=chain_id,
                from_address=from_address or first_step.get("from")
            )
        
        return None
    
    @staticmethod
    def format_amount(amount: float) -> str:
        """
        Format amount to avoid scientific notation.
        Single source of truth for amount formatting.
        
        Args:
            amount: Float amount to format
            
        Returns:
            Formatted string representation
        """
        if amount >= 1:
            return f"{amount:.6f}".rstrip('0').rstrip('.')
        else:
            return f"{amount:.18f}".rstrip('0').rstrip('.')
    
    @staticmethod
    def validate_transaction_data(data: TransactionData) -> bool:
        """
        Validate that transaction data has required fields.
        
        Args:
            data: TransactionData to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['to', 'data', 'value', 'chainId']
        
        for field in required_fields:
            value = getattr(data, field, None)
            if not value:
                logger.warning(f"Transaction data missing or invalid field: {field}")
                return False
        
        # Validate address format (basic check)
        if not isinstance(data.to, str) or not data.to.startswith("0x"):
            logger.warning(f"Invalid 'to' address format: {data.to}")
            return False
        
        # Validate data format
        if not isinstance(data.data, str) or not data.data.startswith("0x"):
            logger.warning(f"Invalid transaction data format: {data.data}")
            return False
        
        return True


# Singleton instance for easy access
transaction_utils = TransactionUtils()
