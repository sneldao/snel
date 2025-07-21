"""
Axelar protocol adapter for cross-chain operations.
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from app.models.token import TokenInfo
from app.services.axelar_service import axelar_service

logger = logging.getLogger(__name__)

class AxelarAdapter:
    """Axelar protocol adapter for cross-chain transfers."""
    
    def __init__(self):
        """Initialize the Axelar protocol adapter."""
        pass

    @property
    def protocol_id(self) -> str:
        return "axelar"

    @property
    def name(self) -> str:
        return "Axelar Network"

    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return list(axelar_service.get_supported_chains().keys())

    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get quote for token transfer using Axelar.
        
        Args:
            from_token: Source token information
            to_token: Destination token information
            amount: Amount to transfer
            chain_id: Source chain ID
            wallet_address: User wallet address
            **kwargs: Additional parameters (may include to_chain_id for cross-chain)
            
        Returns:
            Quote response
        """
        try:
            logger.info(f"Axelar quote request: {amount} {from_token.symbol} -> {to_token.symbol} on chain {chain_id}")
            
            # Check if this is a cross-chain request
            to_chain_id = kwargs.get('to_chain_id')
            
            if to_chain_id and to_chain_id != chain_id:
                # Cross-chain transfer
                logger.info(f"Cross-chain transfer: {chain_id} -> {to_chain_id}")
                return await axelar_service.get_cross_chain_quote(
                    from_token=from_token.symbol,
                    to_token=to_token.symbol,
                    amount=amount,
                    from_chain_id=chain_id,
                    to_chain_id=to_chain_id,
                    wallet_address=wallet_address
                )
            else:
                # Same-chain request - Axelar doesn't handle this
                logger.info(f"Same-chain request on {chain_id} - Axelar not suitable")
                return await axelar_service.get_same_chain_quote(
                    from_token=from_token.symbol,
                    to_token=to_token.symbol,
                    amount=amount,
                    chain_id=chain_id,
                    wallet_address=wallet_address
                )
                
        except Exception as e:
            logger.exception(f"Error in Axelar quote: {e}")
            return {
                "error": "Failed to get Axelar quote",
                "technical_details": str(e)
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build transaction for Axelar transfer.
        
        Args:
            quote: Quote from get_quote
            chain_id: Chain ID for transaction
            **kwargs: Additional parameters
            
        Returns:
            Transaction data
        """
        try:
            if not quote.get("success"):
                return {
                    "error": "Invalid quote provided",
                    "technical_details": "Quote does not indicate success"
                }
                
            steps = quote.get("steps", [])
            if not steps:
                return {
                    "error": "No transaction steps found in quote",
                    "technical_details": "Quote missing steps"
                }
                
            # For Axelar, the transaction is typically a simple transfer to deposit address
            step = steps[0]
            
            transaction = {
                "to": step.get("to"),
                "value": step.get("value", "0"),
                "data": step.get("data", "0x"),
                "gas": "21000",  # Standard transfer gas
                "gasPrice": None,  # Let wallet determine
            }
            
            return {
                "success": True,
                "transaction": transaction,
                "protocol": "axelar",
                "description": f"Cross-chain transfer via Axelar",
                "steps": steps
            }
            
        except Exception as e:
            logger.exception(f"Error building Axelar transaction: {e}")
            return {
                "error": "Failed to build transaction",
                "technical_details": str(e)
            }

    def is_supported(self, chain_id: int) -> bool:
        """Check if chain is supported by Axelar."""
        return axelar_service.is_chain_supported(chain_id)

    def supports_cross_chain(self) -> bool:
        """Axelar supports cross-chain operations."""
        return True

    def get_supported_tokens(self, chain_id: int) -> list[str]:
        """Get supported tokens for a chain."""
        return axelar_service.get_supported_tokens_for_chain(chain_id)

    async def estimate_gas(
        self,
        quote: Dict[str, Any],
        chain_id: int
    ) -> Dict[str, Any]:
        """
        Estimate gas for Axelar transaction.
        
        Args:
            quote: Quote from get_quote
            chain_id: Chain ID
            
        Returns:
            Gas estimate
        """
        try:
            # Axelar transfers are typically simple transfers
            return {
                "gas_limit": "21000",
                "gas_price": None,  # Let wallet determine
                "estimated_cost_usd": quote.get("estimated_fee", "0.01")
            }
        except Exception as e:
            logger.exception(f"Error estimating Axelar gas: {e}")
            return {
                "error": "Failed to estimate gas",
                "technical_details": str(e)
            }

# Create instance
axelar_adapter = AxelarAdapter()