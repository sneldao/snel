"""
Centralized error guidance service.
Provides consistent, helpful error messages and suggestions across all command types.
Single source of truth for user-facing error guidance.

Core Principle: Help users, don't abandon them.
"""
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from app.models.unified_models import CommandType, UnifiedResponse, AgentType

logger = logging.getLogger(__name__)


class ErrorContext(Enum):
    """Context for error guidance - helps determine appropriate suggestions."""
    MISSING_AMOUNT = "missing_amount"
    MISSING_TOKEN = "missing_token"
    MISSING_DESTINATION = "missing_destination"
    MISSING_TOKEN_PAIR = "missing_token_pair"  # For swaps
    MISSING_CHAIN = "missing_chain"
    INVALID_AMOUNT = "invalid_amount"
    INVALID_ADDRESS = "invalid_address"
    UNSUPPORTED_CHAIN = "unsupported_chain"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    SLIPPAGE_ERROR = "slippage_error"
    NO_LIQUIDITY = "no_liquidity"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    WALLET_NOT_CONNECTED = "wallet_not_connected"
    GENERIC_FAILURE = "generic_failure"
    PRIVACY_OPERATION_FAILED = "privacy_operation_failed"
    PRIVACY_UNSUPPORTED = "privacy_unsupported"
    X402_UNAVAILABLE = "x402_unavailable"
    PROTOCOL_NOT_FOUND = "protocol_not_found"
    RESEARCH_SERVICE_ERROR = "research_service_error"
    RESEARCH_REQUIRED = "research_required"
    RESEARCH_HINT = "research_hint"


class ErrorGuidanceService:
    """
    Provides user-friendly error messages and actionable suggestions.
    Ensures consistent guidance across all command types.
    """

    def __init__(self):
        """Initialize with guidance templates for all command types."""
        self._guidance_templates = self._build_guidance_templates()

    def _build_guidance_templates(self) -> Dict[CommandType, Dict[ErrorContext, Dict[str, Any]]]:
        """Build comprehensive guidance templates for each command type."""
        return {
            CommandType.BRIDGE: {
                ErrorContext.MISSING_AMOUNT: {
                    "message": "I need to know how much you want to bridge.",
                    "suggestions": [
                        "Try 'bridge 0.5 eth from ethereum to optimism'",
                        "Try 'bridge 100 usdc to arbitrum'",
                        "Specify the amount (e.g., '0.1 eth', '50 usdc')"
                    ]
                },
                ErrorContext.MISSING_TOKEN: {
                    "message": "I need to know which token you want to bridge.",
                    "suggestions": [
                        "Try 'bridge 1 eth from ethereum to optimism'",
                        "Try 'bridge 100 usdc to base'",
                        "Specify the token symbol (e.g., 'eth', 'usdc')"
                    ]
                },
                ErrorContext.MISSING_DESTINATION: {
                    "message": "I need to know where you want to bridge to.",
                    "suggestions": [
                        "Try 'bridge 1 eth from ethereum to optimism'",
                        "Try 'bridge 50 usdc from base to arbitrum'",
                        "Specify destination chain (e.g., 'optimism', 'arbitrum', 'base')"
                    ]
                },
                ErrorContext.MISSING_CHAIN: {
                    "message": "I need to know which chain you're bridging from. Make sure your wallet is connected to the source chain.",
                    "suggestions": [
                        "Connect your wallet to the source chain first",
                        "Try 'bridge 1 eth from ethereum to arbitrum'",
                        "Verify your wallet is on the correct network"
                    ]
                },
                ErrorContext.INSUFFICIENT_BALANCE: {
                    "message": "You don't have enough balance to bridge that amount.",
                    "suggestions": [
                        "Check your balance with 'balance'",
                        "Try bridging a smaller amount",
                        "Ensure your wallet is on the correct chain"
                    ]
                },
                ErrorContext.NO_LIQUIDITY: {
                    "message": "There's not enough liquidity to bridge this amount right now.",
                    "suggestions": [
                        "Try a smaller amount",
                        "Try bridging a different token",
                        "Try again in a few moments when liquidity refreshes"
                    ]
                },
                ErrorContext.EXTERNAL_SERVICE_ERROR: {
                    "message": "Unable to reach the bridge service. Please try again.",
                    "suggestions": [
                        "Check your internet connection",
                        "Wait a moment and try again",
                        "If the problem persists, try a different token or amount"
                    ]
                },
            },
            CommandType.BRIDGE_TO_PRIVACY: {
                ErrorContext.MISSING_AMOUNT: {
                    "message": "I need to know how much you want to bridge privately.",
                    "suggestions": [
                        "Try 'bridge 0.5 eth to zcash'",
                        "Try 'bridge 1 usdc to zcash'",
                        "Specify the amount (e.g., '0.1 eth', '50 usdc')"
                    ]
                },
                ErrorContext.MISSING_TOKEN: {
                    "message": "I need to know which token you want to bridge privately.",
                    "suggestions": [
                        "Try 'bridge 1 eth to zcash'",
                        "Try 'bridge 100 usdc to zcash'",
                        "Specify the token symbol (e.g., 'eth', 'usdc')"
                    ]
                },
                ErrorContext.MISSING_CHAIN: {
                    "message": "I need to know which chain you're on. Make sure your wallet is connected.",
                    "suggestions": [
                        "Connect your wallet first",
                        "Try 'bridge 0.5 eth to zcash'",
                        "Verify your wallet is connected"
                    ]
                },
                ErrorContext.INSUFFICIENT_BALANCE: {
                    "message": "You don't have enough balance to bridge that amount to Zcash.",
                    "suggestions": [
                        "Check your balance with 'balance'",
                        "Try bridging a smaller amount",
                        "Ensure sufficient funds for gas fees"
                    ]
                },
                ErrorContext.EXTERNAL_SERVICE_ERROR: {
                    "message": "Unable to process private bridge right now. Please try again.",
                    "suggestions": [
                        "Check your internet connection",
                        "Wait a moment and try again",
                        "Contact support if the problem persists"
                    ]
                },
            },
            CommandType.SET_PRIVACY_DEFAULT: {
                ErrorContext.PRIVACY_UNSUPPORTED: {
                    "message": "The requested privacy level is not supported on this chain.",
                    "suggestions": [
                        "Try a different privacy level",
                        "Check chain capabilities with 'what privacy options are available'",
                        "Switch to a chain with better privacy support"
                    ]
                },
                ErrorContext.GENERIC_FAILURE: {
                    "message": "Failed to set default privacy level.",
                    "suggestions": [
                        "Try again",
                        "Check your wallet connection",
                        "Use 'set privacy to public' as fallback"
                    ]
                }
            },
            CommandType.OVERRIDE_PRIVACY: {
                ErrorContext.PRIVACY_UNSUPPORTED: {
                    "message": "Cannot override to requested privacy level on this chain.",
                    "suggestions": [
                        "Try 'send this transaction publicly' instead",
                        "Check available options with 'what privacy is available'",
                        "Switch chains for better privacy support"
                    ]
                },
                ErrorContext.GENERIC_FAILURE: {
                    "message": "Failed to override privacy for this transaction.",
                    "suggestions": [
                        "Try the transaction without privacy override",
                        "Check chain capabilities",
                        "Contact support if needed"
                    ]
                }
            },
            CommandType.X402_PRIVACY: {
                ErrorContext.X402_UNAVAILABLE: {
                    "message": "x402 privacy is not available on this chain.",
                    "suggestions": [
                        "Try 'send privately' for GMP-based privacy",
                        "Switch to Ethereum, Base, or Polygon for x402",
                        "Use regular privacy if x402 not required"
                    ]
                },
                ErrorContext.PRIVACY_UNSUPPORTED: {
                    "message": "Privacy operations not supported on this chain.",
                    "suggestions": [
                        "Try a different chain (Ethereum, Base, Polygon)",
                        "Use public transactions",
                        "Check chain capabilities"
                    ]
                },
                ErrorContext.GENERIC_FAILURE: {
                    "message": "x402 privacy transaction failed.",
                    "suggestions": [
                        "Try again with GMP privacy",
                        "Check wallet balance and connection",
                        "Contact support for assistance"
                    ]
                }
            },
            CommandType.SWAP: {
                ErrorContext.MISSING_AMOUNT: {
                    "message": "I need to know how much you want to swap.",
                    "suggestions": [
                        "Try 'swap 1 eth for usdc'",
                        "Try 'swap 100 usdc for eth'",
                        "Specify the amount (e.g., '1 eth', '50 usdc')"
                    ]
                },
                ErrorContext.MISSING_TOKEN_PAIR: {
                    "message": "I need to know which tokens to swap between.",
                    "suggestions": [
                        "Try 'swap 1 eth for usdc'",
                        "Try 'swap 50 usdc for eth on arbitrum'",
                        "Specify both tokens (e.g., 'eth for usdc')"
                    ]
                },
                ErrorContext.MISSING_CHAIN: {
                    "message": "I need to know which chain you're on. Make sure your wallet is connected.",
                    "suggestions": [
                        "Connect your wallet first",
                        "Try 'swap 1 eth for usdc'",
                        "Verify your wallet is on the correct chain"
                    ]
                },
                ErrorContext.INVALID_AMOUNT: {
                    "message": "The swap amount is invalid.",
                    "suggestions": [
                        "Try a positive amount (e.g., '1 eth')",
                        "Try 'swap 1 eth for usdc'",
                        "Amount must be greater than 0"
                    ]
                },
                ErrorContext.INSUFFICIENT_BALANCE: {
                    "message": "You don't have enough balance for this swap.",
                    "suggestions": [
                        "Check your balance with 'balance'",
                        "Try swapping a smaller amount",
                        "Ensure sufficient funds for gas fees"
                    ]
                },
                ErrorContext.NO_LIQUIDITY: {
                    "message": "There's not enough liquidity for this swap pair.",
                    "suggestions": [
                        "Try a smaller amount",
                        "Try a different token pair",
                        "Try again in a few moments when liquidity refreshes"
                    ]
                },
                ErrorContext.SLIPPAGE_ERROR: {
                    "message": "Price slippage is too high. Try again or adjust your amount.",
                    "suggestions": [
                        "Try a smaller swap amount",
                        "Wait a moment and try again when prices stabilize",
                        "Try a different token pair"
                    ]
                },
                ErrorContext.EXTERNAL_SERVICE_ERROR: {
                    "message": "Unable to complete swap. Please try again.",
                    "suggestions": [
                        "Check your internet connection",
                        "Wait a moment and try again",
                        "Try a different amount or token pair"
                    ]
                },
            },
            CommandType.TRANSFER: {
                ErrorContext.MISSING_AMOUNT: {
                    "message": "I need to know how much you want to transfer.",
                    "suggestions": [
                        "Try 'transfer 0.1 eth to 0x123...'",
                        "Try 'transfer 50 usdc to vitalik.eth'",
                        "Specify the amount (e.g., '0.1 eth', '50 usdc')"
                    ]
                },
                ErrorContext.MISSING_TOKEN: {
                    "message": "I need to know which token you want to transfer.",
                    "suggestions": [
                        "Try 'transfer 0.1 eth to 0x123...'",
                        "Try 'transfer 50 usdc to vitalik.eth'",
                        "Specify the token symbol (e.g., 'eth', 'usdc')"
                    ]
                },
                ErrorContext.MISSING_DESTINATION: {
                    "message": "I need to know where to send the tokens.",
                    "suggestions": [
                        "Try 'transfer 0.1 eth to 0x123...'",
                        "Try 'transfer 50 usdc to vitalik.eth'",
                        "Provide an address or ENS name"
                    ]
                },
                ErrorContext.INVALID_ADDRESS: {
                    "message": "The destination address doesn't look valid.",
                    "suggestions": [
                        "Use a valid Ethereum address (0x...)",
                        "Or use an ENS name (name.eth)",
                        "Try 'transfer 0.1 eth to vitalik.eth'"
                    ]
                },
                ErrorContext.INSUFFICIENT_BALANCE: {
                    "message": "You don't have enough balance to transfer that amount.",
                    "suggestions": [
                        "Check your balance with 'balance'",
                        "Try transferring a smaller amount",
                        "Ensure sufficient funds for gas fees"
                    ]
                },
                ErrorContext.EXTERNAL_SERVICE_ERROR: {
                    "message": "Unable to prepare transfer. Please try again.",
                    "suggestions": [
                        "Check your internet connection",
                        "Wait a moment and try again",
                        "Verify the recipient address is correct"
                    ]
                },
            },
            CommandType.BALANCE: {
                ErrorContext.WALLET_NOT_CONNECTED: {
                    "message": "I need to know which wallet to check. Please connect your wallet.",
                    "suggestions": [
                        "Connect your wallet first",
                        "Then try 'balance' again",
                        "You can also ask about a specific token"
                    ]
                },
                ErrorContext.EXTERNAL_SERVICE_ERROR: {
                    "message": "Unable to fetch balance right now. Please try again.",
                    "suggestions": [
                        "Check your internet connection",
                        "Wait a moment and try again",
                        "Ensure your wallet is still connected"
                    ]
                },
            },
            CommandType.PROTOCOL_RESEARCH: {
                ErrorContext.PROTOCOL_NOT_FOUND: {
                    "message": "I couldn't find definitive on-chain or off-chain information about this protocol.",
                    "suggestions": [
                        "Search on Coingecko or CoinMarketCap for price and basic info",
                        "Check the official documentation or Twitter/X for recent updates",
                        "Try a more common name or ticker symbol",
                        "Visit 'defillama.com' for deep protocol analytics"
                    ]
                },
                ErrorContext.RESEARCH_SERVICE_ERROR: {
                    "message": "The automated research service is currently experiencing high latency or connectivity issues.",
                    "suggestions": [
                        "Try searching directly on Google or DuckDuckGo",
                        "Visit 'etherscan.io' or 'basescan.org' to check contract data manually",
                        "Wait a few moments and try your request again",
                        "Ask about a related well-known protocol for comparison"
                    ]
                },
                ErrorContext.GENERIC_FAILURE: {
                    "message": "Something went wrong while analyzing the protocol data.",
                    "suggestions": [
                        "Rephrase your question (e.g., 'research Zcash')",
                        "Check the spelling of the protocol name",
                        "Try searching in a web browser for the latest whitepaper",
                        "Ask me to 'explain the concept of [topic]' instead"
                    ]
                }
            },
            CommandType.GENERAL: {
                ErrorContext.RESEARCH_REQUIRED: {
                    "message": "I don't have enough information to answer that accurately. You might want to do some external research.",
                    "suggestions": [
                        "Search on Google for 'how to use [topic]'",
                        "Check documentation on 'docs.[protocol].org'",
                        "Ask me to 'research [topic]' to see if I can find more info",
                        "Check official Twitter/X for the latest status updates"
                    ]
                },
                ErrorContext.GENERIC_FAILURE: {
                    "message": "I encountered an unexpected issue while processing your request.",
                    "suggestions": [
                        "Try rephrasing your command",
                        "Check your internet connection",
                        "Try again in a few moments",
                        "Search for the error message in a browser"
                    ]
                },
                ErrorContext.RESEARCH_HINT: {
                    "message": "I'm having trouble with that. Sometimes external research can help clarify things.",
                    "suggestions": [
                        "Search on Google/Brave for your specific query",
                        "Check 'etherscan.io' or 'basescan.org' for transaction details",
                        "Visit official documentation for the protocol in question",
                        "Ask me for a broader topic (e.g. 'what is DeFi lending?')"
                    ]
                }
            }
        }

    def get_guidance(
        self,
        command_type: CommandType,
        error_context: ErrorContext,
        missing_params: Optional[List[str]] = None,
        additional_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get error guidance for a specific command and error context.
        
        Args:
            command_type: The type of command that failed
            error_context: The specific error context
            missing_params: List of missing parameters (for contextualized messages)
            additional_message: Extra message to prepend
            
        Returns:
            Dict with 'message' and 'suggestions' keys
        """
        # Get template for this command type and error context
        command_templates = self._guidance_templates.get(command_type, {})
        template = command_templates.get(error_context)

        if not template:
            # Fallback to generic guidance
            return self._get_generic_guidance(command_type, missing_params, additional_message)

        guidance = {
            "message": template["message"],
            "suggestions": template["suggestions"]
        }

        # Enhance message if missing params provided
        if missing_params and error_context in [
            ErrorContext.MISSING_AMOUNT,
            ErrorContext.MISSING_TOKEN,
            ErrorContext.MISSING_DESTINATION,
            ErrorContext.MISSING_CHAIN,
        ]:
            params_str = ", ".join(missing_params)
            guidance["message"] = f"I need more information. Please provide: {params_str}.\n\n{template['message']}"

        # Add any additional message
        if additional_message:
            guidance["message"] = f"{additional_message}\n\n{guidance['message']}"

        return guidance

    def _get_generic_guidance(
        self,
        command_type: CommandType,
        missing_params: Optional[List[str]] = None,
        additional_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get generic guidance for unknown error contexts."""
        command_name = command_type.value.lower()
        
        guidance = {
            "message": f"I encountered an issue with your {command_name} request. Please try again with a well-formed command.",
            "suggestions": [
                "Check the command syntax",
                "Ensure all required parameters are provided",
                "Try again in a moment"
            ]
        }

        if missing_params:
            params_str = ", ".join(missing_params)
            guidance["message"] = f"Missing information: {params_str}. {guidance['message']}"

        if additional_message:
            guidance["message"] = f"{additional_message}\n\n{guidance['message']}"

        return guidance

    def create_error_response(
        self,
        command_type: CommandType,
        agent_type: AgentType,
        error_context: ErrorContext,
        missing_params: Optional[List[str]] = None,
        additional_message: Optional[str] = None,
        error: Optional[str] = None
    ) -> UnifiedResponse:
        """
        Create a complete error response with guidance.
        
        This is the main method processors should use for consistent error responses.
        """
        guidance = self.get_guidance(command_type, error_context, missing_params, additional_message)

        return UnifiedResponse(
            content={
                "message": guidance["message"],
                "type": "error",
                "suggestions": guidance["suggestions"],
                "error_context": error_context.value
            },
            agent_type=agent_type,
            status="error",
            error=error or guidance["message"]
        )

    def enhance_error_message(
        self,
        base_message: str,
        command_type: CommandType,
        error_context: Optional[ErrorContext] = None,
        missing_params: Optional[List[str]] = None
    ) -> str:
        """
        Enhance a base error message with contextual guidance.
        Useful for adding guidance to existing error messages.
        """
        if error_context:
            guidance = self.get_guidance(command_type, error_context, missing_params)
            return f"{base_message}\n\n{guidance['message']}"
        
        return base_message


# Create singleton instance
error_guidance_service = ErrorGuidanceService()