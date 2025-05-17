"""
Swap service implementation using multiple protocol aggregators.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from app.services.brian.client import brian_client
from app.services.token_service import token_service
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SwapService:
    async def get_quote(
        self, 
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        protocol_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a quote for swapping tokens.
        Returns user-friendly messages for the frontend and logs technical details.
        """
        try:
            # Log the request
            logger.info(f"Getting quote for swap: {amount} {from_token} -> {to_token} on chain {chain_id}")
            
            # Get token information
            from_token_info = await token_service.get_token_info(chain_id, from_token)
            to_token_info = await token_service.get_token_info(chain_id, to_token)
            
            if not from_token_info or not to_token_info:
                logger.error(f"Token info not found. From: {from_token_info}, To: {to_token_info}")
                return {
                    "error": "One or both tokens are not supported on this chain.",
                    "technical_details": f"Token info not found for {from_token} or {to_token} on chain {chain_id}"
                }

            # Get quote from Brian
            quote = await brian_client.get_swap_transaction(
                from_token=from_token_info["address"] or from_token,
                to_token=to_token_info["address"] or to_token,
                amount=float(amount),
                chain_id=chain_id,
                wallet_address=wallet_address
            )

            # If there's an error, it's already user-friendly from the Brian client
            if "error" in quote:
                logger.error(f"Brian API error: {quote.get('technical_details')}")
                return {
                    "error": quote["message"],
                    "technical_details": quote.get("technical_details", "Unknown error")
                }

            # Log success
            logger.info(f"Successfully got quote from Brian: {quote.get('metadata', {})}")
            
            return {
                "success": True,
                "protocol": "brian",
                "steps": quote["steps"],
                "metadata": quote["metadata"]
            }

        except Exception as e:
            logger.exception("Unexpected error in get_quote")
            return {
                "error": "Unable to get a quote at this time. Please try again later.",
                "technical_details": str(e)
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """Build the transaction for execution."""
        try:
            # The quote already contains the transaction data from Brian
            return {
                "success": True,
                "transaction": quote
            }
        except Exception as e:
            logger.exception("Error building transaction")
            return {
                "error": "Unable to prepare the transaction. Please try again.",
                "technical_details": str(e)
            }

    async def get_token_info(
        self,
        token_address: str,
        chain_id: int,
        protocol_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get token information using the preferred or specified protocol.
        
        Args:
            token_address: Token address to get info for
            chain_id: Chain ID for the token
            protocol_name: Optional specific protocol to use
        """
        protocol = None
        if protocol_name:
            protocol = self.protocol_manager.get_protocol(protocol_name)
            if not protocol or not protocol.is_supported(chain_id):
                return None
        else:
            protocol = self.protocol_manager.get_preferred_protocol(chain_id)
            if not protocol:
                return None

        return await protocol.get_token_info(token_address, chain_id)

# Global instance
swap_service = SwapService()