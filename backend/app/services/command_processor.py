"""
Unified command processor with dependency injection.
Clean, modular, DRY implementation without import chaos.
"""
import logging
from typing import Dict, Any, Optional, Union

from app.models.unified_models import (
    CommandType, UnifiedCommand, UnifiedResponse, AgentType,
    ResponseContent, ValidationResult, TransactionData
)
from app.services.unified_command_parser import UnifiedCommandParser
from app.config.settings import Settings
from app.core.exceptions import (
    ValidationError, 
    BusinessLogicError, 
    ExternalServiceError,
    command_parse_error,
    invalid_amount_error,
    invalid_address_error,
    unsupported_chain_error,
    wallet_not_connected_error
)

logger = logging.getLogger(__name__)


class CommandProcessor:
    """
    Unified command processor with dependency injection.
    Eliminates import chaos and provides consistent service access.
    """
    
    def __init__(self, brian_client, settings: Settings):
        """
        Initialize command processor with dependencies.
        
        Args:
            brian_client: Brian API client instance
            settings: Application settings
        """
        self.brian_client = brian_client
        self.settings = settings

    @staticmethod
    def create_unified_command(
        command: str,
        wallet_address: str = None,
        chain_id: int = None,
        user_name: str = None,
        openai_api_key: str = None
    ) -> UnifiedCommand:
        """Create a unified command using the unified parser."""
        return UnifiedCommandParser.create_unified_command(
            command=command,
            wallet_address=wallet_address,
            chain_id=chain_id,
            user_name=user_name,
            openai_api_key=openai_api_key
        )

    @staticmethod
    def validate_command(unified_command: UnifiedCommand) -> ValidationResult:
        """Validate a unified command."""
        return UnifiedCommandParser.validate_command(unified_command)
    
    async def process_command(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process a command using the appropriate handler."""
        try:
            # Validate wallet connection for transaction commands
            if unified_command.command_type in [CommandType.TRANSFER, CommandType.BRIDGE, CommandType.SWAP]:
                if not unified_command.wallet_address:
                    raise wallet_not_connected_error()
            
            # Validate chain support
            if unified_command.chain_id and unified_command.chain_id not in self.settings.chains.supported_chains:
                raise unsupported_chain_error(
                    unified_command.chain_id, 
                    list(self.settings.chains.supported_chains.keys())
                )
            
            command_type = unified_command.command_type
            
            if command_type == CommandType.TRANSFER:
                return await self._process_transfer(unified_command)
            elif command_type == CommandType.BRIDGE:
                return await self._process_bridge(unified_command)
            elif command_type == CommandType.SWAP:
                return await self._process_swap(unified_command)
            elif command_type == CommandType.BALANCE:
                return await self._process_balance(unified_command)
            elif command_type == CommandType.PORTFOLIO:
                return await self._process_portfolio(unified_command)
            elif command_type == CommandType.PROTOCOL_RESEARCH:
                return await self._process_protocol_research(unified_command)
            elif command_type == CommandType.GREETING:
                return await self._process_greeting(unified_command)
            else:
                return await self._process_unknown(unified_command)
                
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return UnifiedResponse(
                content={
                    "message": e.message,
                    "type": "error",
                    "suggestions": e.suggestions
                },
                agent_type="error",
                status="error",
                error=e.message
            )
        except BusinessLogicError as e:
            logger.warning(f"Business logic error: {e.message}")
            return UnifiedResponse(
                content={
                    "message": e.message,
                    "type": "error",
                    "suggestions": e.suggestions
                },
                agent_type="error",
                status="error",
                error=e.message
            )
        except ExternalServiceError as e:
            logger.error(f"External service error: {e.message}")
            return UnifiedResponse(
                content={
                    "message": e.message,
                    "type": "error",
                    "suggestions": e.suggestions
                },
                agent_type="error",
                status="error",
                error=e.message
            )
        except Exception as e:
            logger.exception(f"Unexpected error processing command: {unified_command.command}")
            return UnifiedResponse(
                content={
                    "message": "I encountered an unexpected error. Please try again.",
                    "type": "error"
                },
                agent_type="error",
                status="error",
                error=str(e)
            )
    
    async def _process_transfer(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process transfer commands using injected Brian client."""
        try:
            logger.info(f"Processing transfer command: {unified_command.command}")

            # Extract and validate transfer details
            details = unified_command.details
            if not details or not details.amount or not details.token_in or not details.destination:
                raise command_parse_error(
                    unified_command.command,
                    "transfer [amount] [token] to [address/ENS]"
                )

            # Validate amount
            if details.amount <= 0:
                raise invalid_amount_error(details.amount)

            # Format amount to avoid scientific notation
            amount_str = self._format_amount(details.amount)

            logger.info(f"Attempting transfer: {amount_str} {details.token_in.symbol} to {details.destination}")

            # Call Brian API for transfer transaction
            result = await self.brian_client.get_transfer_transaction(
                token=details.token_in.symbol,
                amount=amount_str,
                to_address=details.destination,
                chain_id=unified_command.chain_id,
                wallet_address=unified_command.wallet_address
            )

            if "error" in result:
                raise ExternalServiceError(
                    message=result.get("message", "Transfer preparation failed"),
                    service_name="Brian API"
                )

            # Format response content
            content = {
                "message": f"Ready to transfer {amount_str} {details.token_in.symbol} to {details.destination}",
                "amount": amount_str,
                "token": details.token_in.symbol,
                "destination": details.destination,
                "gas_cost_usd": result.get("gasCostUSD", ""),
                "type": "transfer_ready",
                "requires_transaction": True
            }

            # Format transaction data
            transaction_data = self._create_transaction_data(result, unified_command.chain_id)

            return UnifiedResponse(
                content=content,
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                transaction=transaction_data,
                metadata={
                    "parsed_command": {
                        "amount": amount_str,
                        "token": details.token_in.symbol,
                        "destination": details.destination,
                        "command_type": "transfer"
                    },
                    "resolved_address": details.destination,
                    "transaction_ready": True,
                    "description": result.get("description", f"Transfer {amount_str} {details.token_in.symbol}"),
                    "solver": result.get("solver", ""),
                    "protocol": result.get("protocol", {})
                }
            )

        except (ValidationError, BusinessLogicError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            logger.exception("Error processing transfer command")
            raise ExternalServiceError(
                message="Failed to prepare transfer transaction",
                service_name="Transfer Service",
                original_error=str(e)
            )
    
    def _format_amount(self, amount: float) -> str:
        """Format amount to avoid scientific notation."""
        if amount < 1:
            return f"{amount:.18f}".rstrip('0').rstrip('.')
        return str(amount)
    
    def _create_transaction_data(self, result: dict, chain_id: int) -> Optional[TransactionData]:
        """Create transaction data from API result."""
        steps = result.get("steps", [])
        if not steps:
            return None

        first_step = steps[0]
        return TransactionData(
            to=first_step.get("to", ""),
            data=first_step.get("data", "0x"),
            value=str(first_step.get("value", "0")),
            gas_limit=str(first_step.get("gasLimit", "")),
            chain_id=chain_id,
            from_address=first_step.get("from")
        )

    async def _process_bridge(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process bridge commands using injected Brian client."""
        try:
            from app.config.chains import get_chain_id_by_name

            logger.info(f"Processing bridge command: {unified_command.command}")

            # Extract and validate bridge details
            details = unified_command.details
            if not details or not details.amount or not details.token_in or not details.destination_chain:
                raise command_parse_error(
                    unified_command.command,
                    "bridge [amount] [token] to [chain]"
                )

            # Validate amount
            if details.amount <= 0:
                raise invalid_amount_error(details.amount)

            # Get chain IDs
            from_chain_id = unified_command.chain_id
            to_chain_id = get_chain_id_by_name(details.destination_chain)

            if not to_chain_id:
                raise ValidationError(
                    f"Unsupported destination chain: {details.destination_chain}",
                    field="destination_chain",
                    value=details.destination_chain,
                    suggestions=[f"Supported chains: {', '.join(self.settings.chains.supported_chains.values())}"]
                )

            # Get chain names for display
            from_chain_name = self.settings.chains.supported_chains.get(from_chain_id, f"Chain {from_chain_id}")
            to_chain_name = self.settings.chains.supported_chains.get(to_chain_id, f"Chain {to_chain_id}")

            # Format amount
            amount_str = self._format_amount(details.amount)

            logger.info(f"Attempting bridge: {amount_str} {details.token_in.symbol} from {from_chain_id} to {to_chain_id}")

            # Call Brian API for bridge transaction
            result = await self.brian_client.get_bridge_transaction(
                token=details.token_in.symbol,
                amount=amount_str,
                from_chain_id=from_chain_id,
                to_chain_id=to_chain_id,
                wallet_address=unified_command.wallet_address
            )

            # Handle Brian API errors with user-friendly responses
            if "error" in result:
                error_message = result.get("message", "Bridge preparation failed")

                # Return user-friendly error response instead of throwing exception
                return UnifiedResponse(
                    content={
                        "message": error_message,
                        "type": "bridge_error",
                        "from_chain": from_chain_name,
                        "to_chain": to_chain_name,
                        "token": details.token_in.symbol,
                        "amount": amount_str,
                        "suggestions": [
                            "Try a different bridge route",
                            "Check if the token is supported on both chains",
                            "Try bridging ETH instead of other tokens"
                        ]
                    },
                    agent_type=AgentType.BRIDGE,
                    status="error",
                    error=error_message
                )

            # Format response content for successful bridge
            content = {
                "message": f"Ready to bridge {amount_str} {details.token_in.symbol} from {from_chain_name} to {to_chain_name}",
                "amount": amount_str,
                "token": details.token_in.symbol,
                "from_chain": from_chain_name,
                "to_chain": to_chain_name,
                "estimated_time": "5-15 minutes",
                "gas_cost_usd": result.get("gasCostUSD", ""),
                "to_amount": result.get("toAmount", ""),
                "protocol": result.get("protocol", {}).get("name", "Unknown"),
                "type": "bridge_ready",
                "requires_transaction": True
            }

            # Format transaction data
            transaction_data = self._create_transaction_data(result, from_chain_id)

            return UnifiedResponse(
                content=content,
                agent_type=AgentType.BRIDGE,
                status="success",
                awaiting_confirmation=True,
                transaction=transaction_data,
                metadata={
                    "bridge_details": {
                        "from_chain_id": from_chain_id,
                        "to_chain_id": to_chain_id,
                        "amount": amount_str,
                        "token": details.token_in.symbol,
                        "transaction_ready": True
                    },
                    "parsed_command": {
                        "amount": amount_str,
                        "token": details.token_in.symbol,
                        "from_chain": from_chain_name,
                        "to_chain": to_chain_name,
                        "command_type": "bridge"
                    }
                }
            )

        except (ValidationError, BusinessLogicError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            logger.exception("Error processing bridge command")
            raise ExternalServiceError(
                message="Failed to prepare bridge transaction",
                service_name="Bridge Service",
                original_error=str(e)
            )

    async def _process_swap(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process swap commands using injected Brian client."""
        try:
            logger.info(f"Processing swap command: {unified_command.command}")

            # Extract and validate swap details
            details = unified_command.details
            if not details or not details.amount or not details.token_in or not details.token_out:
                raise command_parse_error(
                    unified_command.command,
                    "swap [amount] [token_in] for [token_out]"
                )

            # Validate amount
            if details.amount <= 0:
                raise invalid_amount_error(details.amount)

            # Format amount to avoid scientific notation
            amount_str = self._format_amount(details.amount)

            logger.info(f"Attempting swap: {amount_str} {details.token_in.symbol} for {details.token_out.symbol}")

            # Call Brian API for swap transaction
            result = await self.brian_client.get_swap_transaction(
                from_token=details.token_in.symbol,
                to_token=details.token_out.symbol,
                amount=amount_str,
                chain_id=unified_command.chain_id,
                wallet_address=unified_command.wallet_address
            )

            if "error" in result:
                raise ExternalServiceError(
                    message=result.get("message", "Swap preparation failed"),
                    service_name="Brian API"
                )

            # Format response content
            content = {
                "message": f"Ready to swap {amount_str} {details.token_in.symbol} for {details.token_out.symbol}",
                "amount": amount_str,
                "token_in": details.token_in.symbol,
                "token_out": details.token_out.symbol,
                "gas_cost_usd": result.get("gasCostUSD", ""),
                "type": "swap_ready",
                "requires_transaction": True
            }

            # Format transaction data
            transaction_data = self._create_transaction_data(result, unified_command.chain_id)

            return UnifiedResponse(
                content=content,
                agent_type=AgentType.SWAP,
                status="success",
                awaiting_confirmation=True,
                transaction=transaction_data,
                metadata={
                    "parsed_command": {
                        "amount": amount_str,
                        "token_in": details.token_in.symbol,
                        "token_out": details.token_out.symbol,
                        "command_type": "swap"
                    },
                    "transaction_ready": True,
                    "description": result.get("description", f"Swap {amount_str} {details.token_in.symbol} for {details.token_out.symbol}"),
                    "solver": result.get("solver", ""),
                    "protocol": result.get("protocol", {})
                }
            )

        except (ValidationError, BusinessLogicError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            logger.exception("Error processing swap command")
            raise ExternalServiceError(
                message="Failed to prepare swap transaction",
                service_name="Swap Service",
                original_error=str(e)
            )

    async def _process_balance(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process balance check commands."""
        return UnifiedResponse(
            content={
                "message": "Balance checking functionality coming soon!",
                "type": "info"
            },
            agent_type=AgentType.BALANCE,
            status="success"
        )

    async def _process_portfolio(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process portfolio analysis commands."""
        return UnifiedResponse(
            content={
                "message": "Portfolio analysis functionality coming soon!",
                "type": "info"
            },
            agent_type=AgentType.PORTFOLIO,
            status="success"
        )

    async def _process_protocol_research(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process protocol research commands."""
        return UnifiedResponse(
            content={
                "message": "Protocol research functionality coming soon!",
                "type": "info"
            },
            agent_type=AgentType.PROTOCOL_RESEARCH,
            status="success"
        )

    async def _process_greeting(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process greeting commands."""
        greeting_responses = {
            "gm": "Good morning! How can I help you with crypto today?",
            "good morning": "Good morning! How can I help you with crypto today?",
            "hello": "Hello there! How can I assist you with crypto today?",
            "hi": "Hi! How can I help you with crypto today?",
            "hey": "Hey there! How can I assist you with crypto today?",
            "howdy": "Howdy! How can I help you with crypto today?",
            "sup": "Sup! How can I assist you with crypto today?",
            "yo": "Yo! How can I help you with crypto today?"
        }

        cmd_lower = unified_command.command.lower().strip()
        response_text = greeting_responses.get(cmd_lower, "Hello! How can I help you with crypto today?")

        return UnifiedResponse(
            content={
                "message": response_text,
                "type": "greeting"
            },
            agent_type=AgentType.DEFAULT,
            status="success"
        )

    async def _process_unknown(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process unknown commands."""
        return UnifiedResponse(
            content={
                "message": "I'm not sure how to help with that. Please try a specific command like 'swap', 'transfer', or 'bridge'.",
                "type": "help",
                "suggestions": [
                    "Try 'swap 1 eth for usdc'",
                    "Try 'transfer 0.1 eth to address'",
                    "Try 'bridge 100 usdc to arbitrum'"
                ]
            },
            agent_type=AgentType.DEFAULT,
            status="success"
        )
