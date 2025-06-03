"""
Swap service implementation using multiple protocol aggregators.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import logging
from app.protocols.registry import protocol_registry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SwapService:
    def __init__(self):
        """Initialize the swap service."""
        self.registry = protocol_registry

    async def get_quote(
        self,
        from_token_id: str,
        to_token_id: str,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        protocol_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a quote for swapping tokens with fallback mechanism.

        Args:
            from_token_id: Source token identifier (symbol or address)
            to_token_id: Destination token identifier (symbol or address)
            amount: Amount to swap
            chain_id: Chain ID to use
            wallet_address: User's wallet address
            protocol_id: Optional specific protocol to use

        Returns:
            Quote response or error information
        """
        try:
            # Log the request
            logger.info(f"Getting quote for swap: {amount} {from_token_id} -> {to_token_id} on chain {chain_id}")

            # Resolve token information
            from_token = await self.registry.resolve_token(chain_id, from_token_id)
            to_token = await self.registry.resolve_token(chain_id, to_token_id)

            logger.info(f"From token info: {from_token}")
            logger.info(f"To token info: {to_token}")

            # For Brian protocol, create minimal token objects if resolution fails
            # Brian handles token resolution internally
            if not from_token and protocol_id == "brian":
                logger.info(f"Creating minimal token object for Brian: {from_token_id}")
                from app.models.token import TokenInfo
                from_token = TokenInfo(
                    id=from_token_id.lower(),
                    name=from_token_id.upper(),
                    symbol=from_token_id.upper(),
                    decimals=18,
                    type="unknown",
                    verified=False,
                    addresses={}
                )

            if not to_token and protocol_id == "brian":
                logger.info(f"Creating minimal token object for Brian: {to_token_id}")
                from app.models.token import TokenInfo
                to_token = TokenInfo(
                    id=to_token_id.lower(),
                    name=to_token_id.upper(),
                    symbol=to_token_id.upper(),
                    decimals=18,
                    type="unknown",
                    verified=False,
                    addresses={}
                )

            if not from_token:
                logger.error(f"From token info not found: {from_token_id} on chain {chain_id}")
                return {
                    "error": f"Token '{from_token_id}' is not supported on chain {chain_id}.",
                    "technical_details": f"Token info not found for {from_token_id} on chain {chain_id}",
                    "protocols_tried": [],
                    "suggestion": "Please check the token symbol or try a different token."
                }

            if not to_token:
                logger.error(f"To token info not found: {to_token_id} on chain {chain_id}")
                return {
                    "error": f"Token '{to_token_id}' is not supported on chain {chain_id}.",
                    "technical_details": f"Token info not found for {to_token_id} on chain {chain_id}",
                    "protocols_tried": [],
                    "suggestion": "Please check the token symbol or try a different token."
                }

            # Track which protocols we tried and their specific errors
            tried_protocols = []
            protocol_errors = {}

            # Try using the specified protocol first
            if protocol_id:
                protocol = self.registry.get_protocol(protocol_id)
                if protocol and protocol.is_supported(chain_id):
                    try:
                        logger.info(f"Using specified protocol: {protocol_id}")
                        tried_protocols.append(protocol_id)

                        # Brian protocol handles token resolution internally
                        if protocol_id == "brian":
                            logger.info("Using specified Brian protocol - skipping token validation")

                        protocol_quote = await protocol.get_quote(
                            from_token=from_token,
                            to_token=to_token,
                            amount=amount,
                            chain_id=chain_id,
                            wallet_address=wallet_address
                        )
                        return self._format_quote_response(protocol_quote, chain_id)
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error with specified protocol {protocol_id}: {error_msg}")
                        protocol_errors[protocol_id] = error_msg
                        # Continue to auto-select protocol

            # Get supported protocols and try them in preferred order
            supported_protocols = self.registry.get_supported_protocols(chain_id)
            if not supported_protocols:
                logger.error(f"No protocols support chain {chain_id}")
                return {
                    "error": f"No supported protocols for chain {chain_id}.",
                    "technical_details": "No configured protocols support this chain.",
                    "protocols_tried": tried_protocols,
                    "suggestion": "Try using a different blockchain network."
                }

            # Try each protocol until one works
            error_details = []
            for protocol in supported_protocols:
                protocol_id = protocol.protocol_id
                if protocol_id not in tried_protocols:
                    tried_protocols.append(protocol_id)
                    try:
                        logger.info(f"Trying protocol: {protocol_id}")

                        # Brian protocol handles token resolution internally
                        if protocol_id == "brian":
                            logger.info("Using Brian protocol - skipping token validation")
                            protocol_quote = await protocol.get_quote(
                                from_token=from_token,
                                to_token=to_token,
                                amount=amount,
                                chain_id=chain_id,
                                wallet_address=wallet_address
                            )
                            logger.info(f"Successfully got quote from {protocol_id}")
                            return self._format_quote_response(protocol_quote, chain_id)

                        # For other protocols, check token support
                        if not from_token.is_supported_on_chain(chain_id):
                            error_msg = f"Token {from_token.symbol} is not supported on chain {chain_id}"
                            protocol_errors[protocol_id] = error_msg
                            error_details.append(f"{protocol_id} error: {error_msg}")
                            logger.error(error_msg)
                            continue

                        if not to_token.is_supported_on_chain(chain_id):
                            error_msg = f"Token {to_token.symbol} is not supported on chain {chain_id}"
                            protocol_errors[protocol_id] = error_msg
                            error_details.append(f"{protocol_id} error: {error_msg}")
                            logger.error(error_msg)
                            continue

                        # Get token addresses
                        from_address = from_token.get_address(chain_id)
                        to_address = to_token.get_address(chain_id)

                        if not from_address or not to_address:
                            error_msg = f"Missing token address for {from_token.symbol} or {to_token.symbol} on chain {chain_id}"
                            protocol_errors[protocol_id] = error_msg
                            error_details.append(f"{protocol_id} error: {error_msg}")
                            logger.error(error_msg)
                            continue

                        # Try to get quote
                        protocol_quote = await protocol.get_quote(
                            from_token=from_token,
                            to_token=to_token,
                            amount=amount,
                            chain_id=chain_id,
                            wallet_address=wallet_address
                        )
                        logger.info(f"Successfully got quote from {protocol_id}")
                        return self._format_quote_response(protocol_quote, chain_id)
                    except Exception as e:
                        error_msg = str(e)
                        protocol_errors[protocol_id] = error_msg
                        error_details.append(f"{protocol_id} error: {error_msg}")
                        logger.error(f"{protocol_id} error: {error_msg}")

            # If we get here, all protocols failed
            # Generate a user-friendly suggestion based on common error patterns
            suggestion = "Please try a different token pair or adjust the amount."
            if any("liquidity" in err.lower() for err in protocol_errors.values()):
                suggestion = "This token pair may have insufficient liquidity. Try a smaller amount or a different pair."
            elif any("minimum" in err.lower() for err in protocol_errors.values()):
                suggestion = "The amount may be below the minimum required. Try increasing the amount."
            elif any("slippage" in err.lower() for err in protocol_errors.values()):
                suggestion = "High price impact detected. Try reducing the amount or try again when market conditions improve."

            return {
                "error": "Unable to find a valid swap route for these tokens.",
                "technical_details": " | ".join(error_details),
                "protocols_tried": tried_protocols,
                "protocol_errors": protocol_errors,
                "suggestion": suggestion
            }

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Unexpected error in get_quote: {error_msg}")
            return {
                "error": "An unexpected error occurred. Please try again.",
                "technical_details": error_msg,
                "protocols_tried": tried_protocols if 'tried_protocols' in locals() else [],
                "suggestion": "This might be a temporary issue. Please try again in a few moments."
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int
    ) -> Dict[str, Any]:
        """Build the transaction for execution."""
        try:
            if "protocol" not in quote:
                return {
                    "error": "Invalid quote format. Missing protocol information.",
                    "technical_details": "Quote missing protocol field"
                }

            protocol_id = quote["protocol"]
            protocol = self.registry.get_protocol(protocol_id)

            if not protocol:
                return {
                    "error": f"Protocol {protocol_id} not found.",
                    "technical_details": f"Protocol {protocol_id} not registered"
                }

            transaction = await protocol.build_transaction(
                quote=quote,
                chain_id=chain_id
            )

            return {
                "success": True,
                "transaction": transaction
            }
        except Exception as e:
            logger.exception("Error building transaction")
            return {
                "error": "Unable to prepare the transaction. Please try again.",
                "technical_details": str(e)
            }

    def _format_quote_response(self, quote: Dict[str, Any], chain_id: int) -> Dict[str, Any]:
        """Format a protocol quote response in a standardized format."""
        if not quote.get("success", False):
            return quote

        # Protocol adapters (like Brian) already format responses properly
        # Just add chain_id if missing
        formatted_quote = quote.copy()
        if "chain_id" not in formatted_quote:
            formatted_quote["chain_id"] = chain_id

        return formatted_quote

# Global instance
swap_service = SwapService()