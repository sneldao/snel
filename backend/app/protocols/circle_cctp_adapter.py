"""
Circle CCTP V2 protocol adapter for cross-chain USDC operations.
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from app.models.token import TokenInfo
from app.services.circle_cctp_service import circle_cctp_service

logger = logging.getLogger(__name__)

class CircleCCTPAdapter:
    """Circle CCTP V2 protocol adapter for cross-chain USDC transfers."""
    
    def __init__(self):
        """Initialize the Circle CCTP V2 protocol adapter."""
        pass

    @property
    def protocol_id(self) -> str:
        return "cctp_v2"

    @property
    def name(self) -> str:
        return "Circle CCTP V2"

    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return list(circle_cctp_service.get_supported_chains().keys())

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
        Get quote for USDC transfer using Circle CCTP V2.
        
        Args:
            from_token: Source token information (must be USDC)
            to_token: Destination token information (must be USDC)
            amount: Amount to transfer
            chain_id: Source chain ID
            wallet_address: User wallet address
            **kwargs: Additional parameters (may include to_chain_id for cross-chain)
            
        Returns:
            Quote response
        """
        try:
            logger.info(f"Circle CCTP quote request: {amount} {from_token.symbol} -> {to_token.symbol} on chain {chain_id}")
            
            # Circle CCTP V2 only supports USDC
            if from_token.symbol.upper() != "USDC" or to_token.symbol.upper() != "USDC":
                logger.info(f"Non-USDC tokens requested: {from_token.symbol} -> {to_token.symbol}")
                return {
                    "error": "Circle CCTP V2 only supports USDC transfers",
                    "technical_details": f"Requested: {from_token.symbol} -> {to_token.symbol}",
                    "suggestion": "Use Circle CCTP V2 only for USDC cross-chain transfers"
                }
            
            # Check if this is a cross-chain request
            to_chain_id = kwargs.get('to_chain_id')
            
            if to_chain_id and to_chain_id != chain_id:
                # Cross-chain USDC transfer
                logger.info(f"Cross-chain USDC transfer: {chain_id} -> {to_chain_id}")
                return await circle_cctp_service.get_cross_chain_quote(
                    from_token=from_token.symbol,
                    to_token=to_token.symbol,
                    amount=amount,
                    from_chain_id=chain_id,
                    to_chain_id=to_chain_id,
                    wallet_address=wallet_address
                )
            else:
                # Same-chain request - Circle CCTP doesn't handle this
                logger.info(f"Same-chain request on {chain_id} - Circle CCTP not suitable")
                return await circle_cctp_service.get_same_chain_quote(
                    from_token=from_token.symbol,
                    to_token=to_token.symbol,
                    amount=amount,
                    chain_id=chain_id,
                    wallet_address=wallet_address
                )
                
        except Exception as e:
            logger.exception(f"Error in Circle CCTP quote: {e}")
            return {
                "error": "Failed to get Circle CCTP quote",
                "technical_details": str(e)
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build transaction for Circle CCTP transfer.
        
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
                
            # For Circle CCTP, we need to handle multi-step transactions (approve + burn)
            # Return the first step (approval) as the main transaction
            first_step = steps[0]

            # Determine gas limit based on step type
            gas_limit = first_step.get("gasLimit", "100000")

            transaction = {
                "to": first_step.get("to"),
                "value": first_step.get("value", "0"),
                "data": first_step.get("data", "0x"),
                "gasLimit": gas_limit,
                "gasPrice": None,  # Let wallet determine
            }
            
            return {
                "success": True,
                "transaction": transaction,
                "protocol": "cctp_v2",
                "description": f"Cross-chain USDC transfer via Circle CCTP V2",
                "steps": steps
            }
            
        except Exception as e:
            logger.exception(f"Error building Circle CCTP transaction: {e}")
            return {
                "error": "Failed to build transaction",
                "technical_details": str(e)
            }

    def is_supported(self, chain_id: int) -> bool:
        """Check if chain is supported by Circle CCTP V2."""
        return circle_cctp_service.is_chain_supported(chain_id)

    def supports_cross_chain(self) -> bool:
        """Circle CCTP V2 supports cross-chain operations."""
        return True

    async def get_supported_tokens(self, chain_id: int) -> List[str]:
        """Get supported tokens for a chain."""
        return await circle_cctp_service.get_supported_tokens_for_chain(chain_id)

    async def estimate_gas(
        self,
        quote: Dict[str, Any],
        chain_id: int
    ) -> Dict[str, Any]:
        """
        Estimate gas for Circle CCTP transaction.
        
        Args:
            quote: Quote from get_quote
            chain_id: Chain ID
            
        Returns:
            Gas estimate
        """
        try:
            # Circle CCTP transfers involve approve + burn operations
            steps = quote.get("steps", [])
            if not steps:
                return {
                    "error": "No steps found in quote",
                    "technical_details": "Cannot estimate gas without transaction steps"
                }
            
            # Estimate gas for the current step
            first_step = steps[0]
            step_type = first_step.get("type", "unknown")
            
            if step_type == "approve":
                gas_limit = "60000"
            elif step_type == "burn_and_mint":
                gas_limit = "200000"
            else:
                gas_limit = "100000"
            
            return {
                "gas_limit": gas_limit,
                "gas_price": None,  # Let wallet determine
                "estimated_cost_usd": quote.get("estimated_fee", "0.01"),
                "steps_count": len(steps),
                "current_step": 1
            }
        except Exception as e:
            logger.exception(f"Error estimating Circle CCTP gas: {e}")
            return {
                "error": "Failed to estimate gas",
                "technical_details": str(e)
            }

    async def get_transfer_status(self, tx_hash: str, chain_id: int) -> Dict[str, Any]:
        """
        Get status of Circle CCTP transfer.
        
        Args:
            tx_hash: Transaction hash of the burn transaction
            chain_id: Source chain ID
            
        Returns:
            Transfer status information
        """
        try:
            # This would integrate with Circle's attestation service
            # For now, return a basic status structure
            return {
                "status": "pending",
                "tx_hash": tx_hash,
                "chain_id": chain_id,
                "message": "Transfer initiated. Waiting for attestation.",
                "estimated_completion": "1-3 minutes"
            }
        except Exception as e:
            logger.exception(f"Error getting Circle CCTP transfer status: {e}")
            return {
                "error": "Failed to get transfer status",
                "technical_details": str(e)
            }

# Create instance
circle_cctp_adapter = CircleCCTPAdapter()
