"""
Unified command processor with dependency injection.
Clean, modular, DRY implementation without import chaos.
"""
import logging
from typing import Dict, Any, Optional, Union
from openai import AsyncOpenAI

from app.models.unified_models import (
    CommandType, UnifiedCommand, UnifiedResponse, AgentType,
    ResponseContent, ValidationResult, TransactionData
)
from app.services.unified_command_parser import UnifiedCommandParser
from app.config.settings import Settings
from app.services.chat_history import chat_history_service
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
    
    def __init__(self, brian_client, settings: Settings, transaction_flow_service=None):
        """
        Initialize command processor with dependencies.

        Args:
            brian_client: Brian API client instance
            settings: Application settings
            transaction_flow_service: Transaction flow service for multi-step transactions
        """
        self.brian_client = brian_client
        self.settings = settings
        self.transaction_flow_service = transaction_flow_service
        
        # Import protocol registry for Axelar support
        from app.protocols.registry import protocol_registry
        self.protocol_registry = protocol_registry
        
        # Import GMP service for advanced cross-chain operations
        from app.services.axelar_gmp_service import axelar_gmp_service
        self.gmp_service = axelar_gmp_service
        
        # Import enhanced cross-chain handler for GMP operations
        from app.services.enhanced_crosschain_handler import enhanced_crosschain_handler
        self.gmp_handler = enhanced_crosschain_handler

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
    
    async def _classify_with_ai(self, unified_command: UnifiedCommand) -> CommandType:
        """Use AI to classify ambiguous commands based on context."""
        import os
        openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return CommandType.UNKNOWN

        try:
            # Get recent conversation context
            context = chat_history_service.get_recent_context(
                unified_command.wallet_address,
                unified_command.user_name,
                num_messages=5
            )

            client = AsyncOpenAI(api_key=openai_key)

            prompt = f"""
You are a DeFi assistant analyzing user commands. Based on the conversation context and the current command, classify the command type.

RECENT CONVERSATION CONTEXT:
{context}

CURRENT COMMAND: "{unified_command.command}"

Command types available:
- CONTEXTUAL_QUESTION: Questions about previously discussed topics, about you (the assistant), your capabilities, or general crypto/finance topics that require knowledge and reasoning
- PROTOCOL_RESEARCH: Research requests about DeFi protocols
- TRANSFER: Token transfer requests
- BRIDGE: Cross-chain bridge requests
- SWAP: Token swap requests (same chain)
- CROSS_CHAIN_SWAP: Advanced cross-chain swaps using Axelar GMP (e.g., "swap USDC from Ethereum to MATIC on Polygon")
- GMP_OPERATION: General Message Passing operations like cross-chain contract calls, complex DeFi operations across chains
- BALANCE: Balance check requests
- PORTFOLIO: Portfolio analysis requests
- GREETING: Only simple greetings like "hi", "hello", "hey", without other content
- CONFIRMATION: Yes/no confirmations
- UNKNOWN: Unclear or unrelated commands

Classification guidelines:
- Questions about who you are, what you can do, or your capabilities → CONTEXTUAL_QUESTION (not GREETING)
- Questions that require explanations or detailed responses → CONTEXTUAL_QUESTION
- Only classify as GREETING if it's a simple hello with no other content
- If the user is asking about something that was recently discussed → CONTEXTUAL_QUESTION
- Cross-chain swaps with different tokens or chains → CROSS_CHAIN_SWAP
- Complex cross-chain operations (yield farming, liquidity provision across chains) → GMP_OPERATION
- Contract calls on different chains → GMP_OPERATION
- Simple same-chain swaps → SWAP

Examples:
- "swap 100 USDC from Ethereum to MATIC on Polygon" → CROSS_CHAIN_SWAP
- "call mint function on Polygon using funds from Ethereum" → GMP_OPERATION
- "add liquidity to Uniswap on Arbitrum using ETH from Ethereum" → GMP_OPERATION
- "swap 1 ETH for USDC" → SWAP
- "bridge 100 USDC to Arbitrum" → BRIDGE

Respond with ONLY the command type name (e.g., "CROSS_CHAIN_SWAP").
"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a command classifier. Respond with only the command type name."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0.1
            )

            ai_classification = response.choices[0].message.content.strip().upper()

            # Map AI response to CommandType enum
            try:
                return CommandType(ai_classification.lower())
            except ValueError:
                logger.warning(f"AI returned unknown command type: {ai_classification}")
                return CommandType.UNKNOWN

        except Exception as e:
            logger.error(f"AI classification failed: {str(e)}")
            return CommandType.UNKNOWN

    async def process_command(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process a command using the appropriate handler."""
        try:
            # If command was classified as UNKNOWN, try AI classification
            if unified_command.command_type == CommandType.UNKNOWN:
                ai_classification = await self._classify_with_ai(unified_command)
                if ai_classification != CommandType.UNKNOWN:
                    unified_command.command_type = ai_classification
                    logger.info(f"AI reclassified command '{unified_command.command}' as {ai_classification}")

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
            
            # Check if this is a GMP operation first (before processing as regular commands)
            if await self._should_use_gmp_handler(unified_command):
                return await self._process_gmp_operation(unified_command)
            
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
            elif command_type == CommandType.CONTEXTUAL_QUESTION:
                return await self._process_contextual_question(unified_command)
            elif command_type == CommandType.GREETING:
                return await self._process_greeting(unified_command)
            elif command_type == CommandType.GMP_OPERATION:
                return await self._process_gmp_operation(unified_command)
            elif command_type == CommandType.CROSS_CHAIN_SWAP:
                return await self._process_cross_chain_swap(unified_command)
            elif command_type == CommandType.TRANSACTION_STEP_COMPLETE:
                return await self._process_transaction_step_complete(unified_command)
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

    def _create_transaction_data_from_quote(self, quote: dict, chain_id: int) -> Optional[TransactionData]:
        """Create transaction data from protocol quote."""
        if not quote.get("success", False):
            return None
            
        # Handle different quote formats
        if "transaction" in quote:
            # Single transaction format
            tx = quote["transaction"]
            return TransactionData(
                to=tx.get("to", ""),
                data=tx.get("data", "0x"),
                value=str(tx.get("value", "0")),
                gas_limit=str(tx.get("gas_limit", tx.get("gasLimit", ""))),
                chain_id=chain_id,
                from_address=tx.get("from")
            )
        elif "steps" in quote and quote["steps"]:
            # Multi-step format
            first_step = quote["steps"][0]
            return TransactionData(
                to=first_step.get("to", ""),
                data=first_step.get("data", "0x"),
                value=str(first_step.get("value", "0")),
                gas_limit=str(first_step.get("gasLimit", first_step.get("gas_limit", ""))),
                chain_id=chain_id,
                from_address=first_step.get("from")
            )
        
        return None

    def _detect_cross_chain_intent(self, command: str, details) -> bool:
        """Detect if the user intends a cross-chain operation."""
        command_lower = command.lower()
        
        # Look for explicit cross-chain keywords
        cross_chain_keywords = [
            "bridge", "cross-chain", "cross chain", "to arbitrum", "to polygon",
            "to ethereum", "to base", "to optimism", "from arbitrum", "from polygon",
            "from ethereum", "from base", "from optimism"
        ]
        
        for keyword in cross_chain_keywords:
            if keyword in command_lower:
                return True
        
        # Check if tokens suggest different chains (basic heuristic)
        # This could be enhanced with a token-to-chain mapping
        if details and details.token_in and details.token_out:
            # For now, assume same-chain unless explicitly specified
            # This could be enhanced with better token analysis
            pass
        
        return False

    def _infer_destination_chain(self, token_symbol: str, from_chain: int) -> int:
        """Infer destination chain from token symbol or context."""
        # For now, return the same chain
        # This could be enhanced with token-to-chain mapping
        # or by parsing the command for chain names
        return from_chain

    async def _process_bridge(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process bridge commands using protocol registry with Axelar priority."""
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

            # Use protocol registry to get quote with Axelar priority for cross-chain
            quote = await self.protocol_registry.get_quote(
                from_token=details.token_in.symbol,
                to_token=details.token_in.symbol,  # Same token for bridging
                amount=amount_str,
                from_chain=from_chain_id,
                to_chain=to_chain_id,
                user_address=unified_command.wallet_address
            )
            
            if not quote or not quote.get("success", False):
                return UnifiedResponse(
                    content={
                        "message": "Cross-chain routing unavailable",
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
                    error="Cross-chain routing unavailable"
                )
            
            # Create transaction data from quote
            transaction_data = self._create_transaction_data_from_quote(quote, from_chain_id)
            if not transaction_data:
                return UnifiedResponse(
                    content={
                        "message": "Failed to create bridge transaction",
                        "type": "bridge_error",
                        "from_chain": from_chain_name,
                        "to_chain": to_chain_name,
                        "token": details.token_in.symbol,
                        "amount": amount_str,
                        "suggestions": [
                            "Try again in a moment",
                            "Check if the bridge amount is valid",
                            "Verify token is supported on both chains"
                        ]
                    },
                    agent_type=AgentType.BRIDGE,
                    status="error",
                    error="Failed to create bridge transaction"
                )

            # Format response content based on protocol used
            protocol_name = quote.get("protocol", "unknown")
            if protocol_name == "axelar":
                content = {
                    "message": f"Ready to bridge {amount_str} {details.token_in.symbol} via Axelar Network",
                    "amount": amount_str,
                    "token": details.token_in.symbol,
                    "from_chain": from_chain_name,
                    "to_chain": to_chain_name,
                    "protocol": protocol_name,
                    "estimated_time": quote.get("estimated_time", "5-15 minutes"),
                    "estimated_fee": quote.get("estimated_fee", ""),
                    "type": "bridge_ready",
                    "requires_transaction": True
                }
            else:
                content = {
                    "message": f"Ready to bridge {amount_str} {details.token_in.symbol} from {from_chain_name} to {to_chain_name}",
                    "amount": amount_str,
                    "token": details.token_in.symbol,
                    "from_chain": from_chain_name,
                    "to_chain": to_chain_name,
                    "protocol": protocol_name,
                    "estimated_time": "5-15 minutes",
                    "gas_cost_usd": quote.get("gas_cost_usd", ""),
                    "type": "bridge_ready",
                    "requires_transaction": True
                }

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
                        "command_type": "bridge",
                        "protocol": protocol_name
                    },
                    "protocol_used": protocol_name,
                    "quote_data": quote
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
        """Process swap commands using protocol registry with Axelar priority."""
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

            # Determine if this is cross-chain based on token symbols or explicit chain specification
            # This is a simple heuristic - could be enhanced with better parsing
            from_chain = unified_command.chain_id
            to_chain = unified_command.chain_id  # Default to same chain
            
            # Enhanced cross-chain detection
            is_cross_chain = self._detect_cross_chain_intent(unified_command.command, details)
            if is_cross_chain:
                # For cross-chain, we might need to infer the destination chain
                # This could be enhanced with better parsing
                to_chain = self._infer_destination_chain(details.token_out.symbol, from_chain)

            logger.info(f"Cross-chain operation: {is_cross_chain}, from_chain: {from_chain}, to_chain: {to_chain}")

            # Use protocol registry to get quote with Axelar priority
            quote = await self.protocol_registry.get_quote(
                from_token=details.token_in.symbol,
                to_token=details.token_out.symbol,
                amount=amount_str,
                from_chain=from_chain,
                to_chain=to_chain,
                user_address=unified_command.wallet_address
            )
            
            if not quote or not quote.get("success", False):
                return UnifiedResponse(
                    content={
                        "message": "No valid quote available for this swap",
                        "type": "swap_error",
                        "suggestions": [
                            "Try a different token pair",
                            "Check if tokens are supported on this chain",
                            "Try again in a moment"
                        ]
                    },
                    agent_type=AgentType.SWAP,
                    status="error",
                    error="No valid quote available for this swap"
                )
            
            # Create transaction data from quote
            transaction_data = self._create_transaction_data_from_quote(quote, from_chain)
            if not transaction_data:
                return UnifiedResponse(
                    content={
                        "message": "Failed to create transaction data",
                        "type": "swap_error",
                        "suggestions": [
                            "Try again in a moment",
                            "Check if the swap amount is valid",
                            "Verify token addresses are correct"
                        ]
                    },
                    agent_type=AgentType.SWAP,
                    status="error",
                    error="Failed to create transaction data"
                )
            
            # Format response content based on protocol used
            protocol_name = quote.get("protocol", "unknown")
            if protocol_name == "axelar":
                content = {
                    "message": f"Ready to bridge {amount_str} {details.token_in.symbol} via Axelar Network",
                    "amount": amount_str,
                    "token_in": details.token_in.symbol,
                    "token_out": details.token_out.symbol,
                    "protocol": protocol_name,
                    "estimated_time": quote.get("estimated_time", "5-15 minutes"),
                    "estimated_fee": quote.get("estimated_fee", ""),
                    "type": "cross_chain_ready",
                    "requires_transaction": True
                }
            else:
                # Add protocol attribution for trust and transparency
                protocol_display = {
                    "brian": "Brian AI",
                    "0x": "0x Protocol",
                    "uniswap": "Uniswap"
                }.get(protocol_name, protocol_name.title())
                
                content = {
                    "message": f"Ready to swap {amount_str} {details.token_in.symbol} for {details.token_out.symbol} via {protocol_display}",
                    "amount": amount_str,
                    "token_in": details.token_in.symbol,
                    "token_out": details.token_out.symbol,
                    "protocol": protocol_name,
                    "gas_cost_usd": quote.get("gas_cost_usd", ""),
                    "type": "swap_ready",
                    "requires_transaction": True
                }

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
                        "command_type": "swap",
                        "protocol": protocol_name
                    },
                    "transaction_ready": True,
                    "protocol_used": protocol_name,
                    "is_cross_chain": is_cross_chain,
                    "quote_data": quote
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
        """Process balance check commands using Brian API."""
        try:
            logger.info(f"Processing balance command: {unified_command.command}")

            # Extract token if specified
            details = unified_command.details
            token = details.token_in.symbol if details and details.token_in else None

            # Validate wallet connection
            if not unified_command.wallet_address:
                raise wallet_not_connected_error()

            # Get chain name for display
            chain_name = self.settings.chains.supported_chains.get(
                unified_command.chain_id,
                f"Chain {unified_command.chain_id}"
            )

            logger.info(f"Checking balance for {unified_command.wallet_address} on {chain_name}")
            if token:
                logger.info(f"Specific token requested: {token}")

            # Call Brian API for balance check
            result = await self.brian_client.get_balance(
                wallet_address=unified_command.wallet_address,
                chain_id=unified_command.chain_id,
                token=token
            )

            if "error" in result:
                # Return user-friendly error response
                return UnifiedResponse(
                    content={
                        "message": result.get("message", "Unable to check balance"),
                        "type": "balance_error",
                        "chain": chain_name,
                        "token": token or "All tokens",
                        "suggestions": [
                            "Try again in a moment",
                            "Check if you're on a supported network",
                            "Verify your wallet is connected"
                        ]
                    },
                    agent_type=AgentType.BALANCE,
                    status="error",
                    error=result.get("message", "Balance check failed")
                )

            # Format successful balance response
            balance_data = result.get("balance_data", {})

            content = {
                "message": f"Balance check complete for {chain_name}",
                "type": "balance_result",
                "chain": chain_name,
                "address": unified_command.wallet_address,
                "token": token or "All tokens",
                "balance_data": balance_data,
                "requires_transaction": False
            }

            return UnifiedResponse(
                content=content,
                agent_type=AgentType.BALANCE,
                status="success",
                metadata={
                    "parsed_command": {
                        "token": token,
                        "chain": chain_name,
                        "command_type": "balance"
                    },
                    "balance_details": {
                        "chain_id": unified_command.chain_id,
                        "wallet_address": unified_command.wallet_address,
                        "token_filter": token
                    }
                }
            )

        except (ValidationError, BusinessLogicError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            logger.exception("Error processing balance command")
            raise ExternalServiceError(
                message="Failed to check balance",
                service_name="Balance Service",
                original_error=str(e)
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
        """Process protocol research commands using Firecrawl and AI analysis."""
        try:
            from app.services.external.firecrawl_service import get_protocol_details, analyze_protocol_with_ai

            logger.info(f"Processing protocol research command: {unified_command.command}")

            # Extract protocol name from command
            details = unified_command.details
            protocol_name = None

            # Try to extract protocol name from various sources
            if details and details.token_in and details.token_in.symbol:
                protocol_name = details.token_in.symbol
            elif details and hasattr(details, 'protocol_name'):
                protocol_name = details.protocol_name
            else:
                # Try to extract from the command text
                command_lower = unified_command.command.lower()
                # Look for common patterns like "research X", "tell me about X", "what is X"
                import re
                patterns = [
                    r'research\s+(\w+)',
                    r'tell me about\s+(\w+)',
                    r'what is\s+(\w+)',
                    r'about\s+(\w+)',
                    r'info on\s+(\w+)',
                    r'explain\s+(\w+)'
                ]

                for pattern in patterns:
                    match = re.search(pattern, command_lower)
                    if match:
                        protocol_name = match.group(1)
                        break

            if not protocol_name:
                return UnifiedResponse(
                    content={
                        "message": "Please specify a protocol to research. For example: 'research Uniswap' or 'tell me about Aave'",
                        "type": "protocol_research_error",
                        "suggestions": [
                            "research Uniswap",
                            "tell me about Aave",
                            "what is Compound",
                            "explain Curve protocol"
                        ]
                    },
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    status="error",
                    error="No protocol specified"
                )

            logger.info(f"Researching protocol: {protocol_name}")

            # First, scrape the protocol content using Firecrawl
            scrape_result = await get_protocol_details(
                protocol_name=protocol_name,
                max_content_length=2000,  # Increased for better AI analysis
                timeout=15,
                debug=True
            )

            if not scrape_result.get("scraping_success", False):
                # Return user-friendly error response
                return UnifiedResponse(
                    content={
                        "message": f"Unable to find detailed information about {protocol_name}. The protocol might not exist or our research service is temporarily unavailable.",
                        "type": "protocol_research_error",
                        "protocol": protocol_name,
                        "suggestions": [
                            "Check the protocol name spelling",
                            "Try researching a well-known protocol like Uniswap or Aave",
                            "Try again in a moment"
                        ]
                    },
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    status="error",
                    error=scrape_result.get("error", "Research failed")
                )

            # Now analyze the scraped content with AI
            # Use user-provided key or fall back to environment variable
            import os
            openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
            logger.info(f"Starting AI analysis for {protocol_name}. OpenAI key available: {bool(openai_key)}")
            ai_result = await analyze_protocol_with_ai(
                protocol_name=protocol_name,
                raw_content=scrape_result.get("raw_content", ""),
                source_url=scrape_result.get("source_url", ""),
                openai_api_key=openai_key
            )
            logger.info(f"AI analysis completed for {protocol_name}. Success: {ai_result.get('analysis_success', False)}")

            # Combine scraping and AI analysis results
            result = {
                **scrape_result,
                **ai_result,
                "type": "protocol_research_result"
            }

            # Format successful research response with AI analysis
            content = {
                "message": f"Research complete for {protocol_name}",
                "type": "protocol_research_result",
                "protocol_name": protocol_name,
                "ai_summary": result.get("ai_summary", ""),
                "protocol_type": result.get("protocol_type", "DeFi Protocol"),
                "key_features": result.get("key_features", []),
                "security_info": result.get("security_info", ""),
                "financial_metrics": result.get("financial_metrics", ""),
                "analysis_quality": result.get("analysis_quality", "medium"),
                "source_url": result.get("source_url", ""),
                "raw_content": result.get("raw_content", ""),
                "analysis_success": result.get("analysis_success", False),
                "content_length": result.get("content_length", 0),
                "requires_transaction": False
            }

            return UnifiedResponse(
                content=content,
                agent_type=AgentType.PROTOCOL_RESEARCH,
                status="success",
                metadata={
                    "parsed_command": {
                        "protocol": protocol_name,
                        "command_type": "protocol_research"
                    },
                    "research_details": {
                        "protocols_scraped": result.get("protocols_scraped", 1),
                        "scraping_success": result.get("scraping_success", False),
                        "source": result.get("source", "firecrawl")
                    }
                }
            )

        except Exception as e:
            logger.exception("Error processing protocol research command")
            return UnifiedResponse(
                content={
                    "message": f"Protocol research service is temporarily unavailable. Please try again later.",
                    "type": "protocol_research_error",
                    "suggestions": [
                        "Try again in a moment",
                        "Check your internet connection",
                        "Try researching a different protocol"
                    ]
                },
                agent_type=AgentType.PROTOCOL_RESEARCH,
                status="error",
                error=str(e)
            )

    async def _process_greeting(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process greeting and self-awareness commands."""
        import os
        
        # Get recent conversation context
        context = chat_history_service.get_recent_context(
            unified_command.wallet_address,
            unified_command.user_name,
            num_messages=5
        )
        
        # If it's a simple greeting (one or two words), use canned responses for speed
        cmd_lower = unified_command.command.lower().strip()
        simple_greetings = {
            "gm": "Good morning! How can I help you with crypto today?",
            "good morning": "Good morning! How can I help you with crypto today?",
            "hello": "Hello there! How can I assist you with crypto today?",
            "hi": "Hi! How can I help you with crypto today?",
            "hey": "Hey there! How can I assist you with crypto today?",
            "howdy": "Howdy! How can I help you with crypto today?",
            "sup": "Sup! How can I assist you with crypto today?",
            "yo": "Yo! How can I help you with crypto today?"
        }
        
        if cmd_lower in simple_greetings:
            return UnifiedResponse(
                content={
                    "message": simple_greetings[cmd_lower],
                    "type": "greeting"
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )
            
        # For more complex questions like "who are you?" or "what can you do?", use the LLM
        try:
            openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                # Fallback to canned response if no API key
                about_snel = (
                    "I'm SNEL — Stablecoin Navigation and Education Leader. "
                    "I help with stablecoin info, RWA insights, risk assessment, portfolio diversification, market data, and DeFi operations. "
                    "Ask me about swaps, bridges, or your portfolio."
                )
                return UnifiedResponse(
                    content={
                        "message": about_snel,
                        "type": "about"
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success"
                )
                
            client = AsyncOpenAI(api_key=openai_key)
            
            # Set of facts about SNEL for the LLM to incorporate in responses
            snel_facts = """
- You are SNEL — Smart, Natural, Efficient, Limitless DeFi Assistant
- You help with stablecoin information and RWA insights
- You provide risk assessment and portfolio diversification advice
- You deliver real-time market data
- You assist with DeFi operations like swaps and bridges
- You specialize in cross-chain operations using Axelar Network's General Message Passing (GMP)
- You can execute complex cross-chain swaps, yield farming, and liquidity provision across 16+ blockchain networks
- You handle multi-step cross-chain operations with natural language commands like "swap USDC from Ethereum to MATIC on Polygon"
- You're built to connect with user wallets for balance checks and portfolio analysis
- You're designed to be conversational and personable
- You're knowledgeable about all aspects of DeFi and cross-chain interoperability
- You use Axelar's secure cross-chain infrastructure for seamless multi-chain operations
"""
            
            prompt = f"""
You are SNEL, a conversational DeFi assistant. The user is asking something about you or what you can do.
Respond in a natural, friendly way while accurately describing your capabilities.

USER QUERY: "{unified_command.command}"

RECENT CONVERSATION CONTEXT:
{context}

FACTS ABOUT YOURSELF:
{snel_facts}

Instructions:
- Be conversational and personable, not robotic
- Be concise but informative (2-4 sentences is ideal)
- Don't use the exact same canned response for similar questions
- Vary your phrasing and personality for each response
- Incorporate your capabilities without listing all of them
- Don't start with "I'm SNEL" for every response
"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are SNEL, a friendly and conversational DeFi assistant. Respond naturally."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7  # Higher temperature for more natural responses
            )

            ai_response = response.choices[0].message.content

            return UnifiedResponse(
                content={
                    "message": ai_response,
                    "type": "about"
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )
        except Exception as e:
            logger.exception(f"Error generating greeting response: {unified_command.command}")
            # Fallback to canned response if AI fails
            about_snel = (
                "I'm SNEL — Stablecoin Navigation and Education Leader. "
                "I help with stablecoin info, RWA insights, risk assessment, portfolio diversification, market data, and DeFi operations. "
                "Ask me about swaps, bridges, or your portfolio."
            )
            return UnifiedResponse(
                content={
                    "message": about_snel,
                    "type": "about"
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )

    async def _process_contextual_question(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process contextual questions using AI and conversation history."""
        try:
            import os
            openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return UnifiedResponse(
                    content={
                        "message": "I need an OpenAI API key to answer contextual questions.",
                        "type": "error"
                    },
                    agent_type=AgentType.DEFAULT,
                    status="error",
                    error="No OpenAI API key"
                )

            # Get recent conversation context
            context = chat_history_service.get_recent_context(
                unified_command.wallet_address,
                unified_command.user_name,
                num_messages=10  # Get more context for better answers
            )
            
            # Set of facts about SNEL for the LLM to incorporate in responses
            snel_facts = """
- You are SNEL — Smart, Natural, Efficient, Limitless DeFi Assistant
- You help with stablecoin information and RWA insights
- You provide risk assessment and portfolio diversification advice
- You deliver real-time market data
- You assist with DeFi operations like swaps and bridges
- You specialize in cross-chain operations using Axelar Network's General Message Passing (GMP)
- You can execute complex cross-chain swaps, yield farming, and liquidity provision across 16+ blockchain networks
- You handle multi-step cross-chain operations with natural language commands like "swap USDC from Ethereum to MATIC on Polygon"
- You're built to connect with user wallets for balance checks and portfolio analysis
- You're designed to be conversational and personable
- You're knowledgeable about all aspects of DeFi and cross-chain interoperability
- You use Axelar's secure cross-chain infrastructure for seamless multi-chain operations
"""

            # Check if this is a question about the assistant itself
            cmd_lower = unified_command.command.lower().strip()
            about_assistant_patterns = [
                "who are you", "what are you", "what can you do", "about you", 
                "about snel", "your purpose", "what is snel", "describe yourself",
                "tell me about you", "capabilities", "features", "help me", 
                "what do you know", "what's your name", "introduce yourself"
            ]
            
            is_about_assistant = any(pattern in cmd_lower for pattern in about_assistant_patterns)

            if not context and not is_about_assistant:
                return UnifiedResponse(
                    content={
                        "message": "I don't have enough context to answer that question. Could you be more specific or ask about a particular protocol?",
                        "type": "contextual_response",
                        "suggestions": [
                            "Try asking 'research Uniswap' first",
                            "Ask about a specific protocol",
                            "Be more specific about what you want to know"
                        ]
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success"
                )

            client = AsyncOpenAI(api_key=openai_key)

            # Adjust the prompt based on whether the question is about the assistant
            prompt = ""
            if is_about_assistant:
                prompt = f"""
You are SNEL, a conversational DeFi assistant. The user is asking something about you or what you can do.
Respond in a natural, friendly way while accurately describing your capabilities.

USER QUERY: "{unified_command.command}"

RECENT CONVERSATION CONTEXT:
{context}

FACTS ABOUT YOURSELF:
{snel_facts}

Instructions:
- Be conversational and personable, not robotic
- Be concise but informative (2-4 sentences is ideal)
- Don't use the exact same canned response for similar questions
- Vary your phrasing and personality for each response
- Incorporate your capabilities without listing all of them
- Don't start with "I'm SNEL" for every response
"""
            else:
                prompt = f"""
You are SNEL, a helpful DeFi assistant. Answer the user's question based on the recent conversation context.

RECENT CONVERSATION CONTEXT:
{context}

USER QUESTION: "{unified_command.command}"

FACTS ABOUT YOURSELF:
{snel_facts}

Instructions:
- Answer based on the conversation context
- If the user is asking about a protocol that was recently researched, provide insights from that research
- Be conversational and helpful, not robotic
- If you can't answer based on the context, say so and suggest what they could ask instead
- Keep responses concise but informative (2-4 sentences)
- Act like an intelligent agent, not a command processor

Respond naturally as if you're having a conversation.
"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are SNEL, a helpful and conversational DeFi assistant. Respond naturally based on conversation context."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7  # Higher temperature for more natural responses
            )
            
            # Log the response for monitoring
            logger.info(f"Generated contextual response for: '{unified_command.command}'")

            ai_response = response.choices[0].message.content

            return UnifiedResponse(
                content={
                    "message": ai_response,
                    "type": "contextual_response"
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )

        except Exception as e:
            logger.exception(f"Error processing contextual question: {unified_command.command}")
            return UnifiedResponse(
                content={
                    "message": "I encountered an error while trying to answer your question. Could you try rephrasing it?",
                    "type": "error"
                },
                agent_type=AgentType.DEFAULT,
                status="error",
                error=str(e)
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

    async def _should_use_gmp_handler(self, unified_command: UnifiedCommand) -> bool:
        """
        Determine if a command should be handled by the GMP handler.
        This checks for complex cross-chain operations that require GMP.
        """
        try:
            # Check if the enhanced cross-chain handler can handle this command
            return await self.gmp_handler.can_handle(unified_command)
        except Exception as e:
            logger.exception(f"Error checking GMP handler capability: {e}")
            return False

    async def _process_gmp_operation(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process general message passing operations using the enhanced cross-chain handler.
        """
        try:
            logger.info(f"Processing GMP operation: {unified_command.command}")

            # Validate wallet connection for GMP operations
            if not unified_command.wallet_address:
                raise wallet_not_connected_error()

            # Determine the type of GMP operation
            if await self._is_cross_chain_swap(unified_command):
                return await self.gmp_handler.handle_cross_chain_swap(
                    unified_command, unified_command.wallet_address
                )
            else:
                return await self.gmp_handler.handle_gmp_operation(
                    unified_command, unified_command.wallet_address
                )

        except (ValidationError, BusinessLogicError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            logger.exception("Error processing GMP operation")
            raise ExternalServiceError(
                message="Failed to process cross-chain operation",
                service_name="GMP Service",
                original_error=str(e)
            )

    async def _process_cross_chain_swap(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process cross-chain swap operations using GMP.
        """
        try:
            logger.info(f"Processing cross-chain swap: {unified_command.command}")

            # Validate wallet connection
            if not unified_command.wallet_address:
                raise wallet_not_connected_error()

            # Use the enhanced cross-chain handler for cross-chain swaps
            return await self.gmp_handler.handle_cross_chain_swap(
                unified_command, unified_command.wallet_address
            )

        except (ValidationError, BusinessLogicError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            logger.exception("Error processing cross-chain swap")
            raise ExternalServiceError(
                message="Failed to process cross-chain swap",
                service_name="Cross-Chain Swap Service",
                original_error=str(e)
            )

    async def _is_cross_chain_swap(self, unified_command: UnifiedCommand) -> bool:
        """
        Determine if this is a cross-chain swap operation.
        """
        try:
            command_text = unified_command.command.lower()
            
            # Check for explicit cross-chain swap patterns
            cross_chain_patterns = [
                r"swap.*from\s+\w+.*to\s+\w+.*on\s+\w+",
                r"bridge.*and.*swap",
                r"cross.chain.*swap",
                r"swap.*on.*\w+.*chain"
            ]
            
            import re
            for pattern in cross_chain_patterns:
                if re.search(pattern, command_text):
                    return True
            
            # Check if different chains are specified
            if hasattr(unified_command, 'from_chain') and hasattr(unified_command, 'to_chain'):
                if (unified_command.from_chain and unified_command.to_chain and 
                    unified_command.from_chain != unified_command.to_chain):
                    return True
            
            return False
            
        except Exception as e:
            logger.exception(f"Error determining if cross-chain swap: {e}")
            return False

    def _convert_gmp_response_to_unified(self, gmp_response: UnifiedResponse) -> UnifiedResponse:
        """
        Convert GMP handler response to unified response format.
        This ensures compatibility with the existing response structure.
        """
        try:
            # If it's already a UnifiedResponse, just update the agent type
            if isinstance(gmp_response, UnifiedResponse):
                # Determine appropriate agent type based on operation
                if gmp_response.content and gmp_response.content.metadata:
                    metadata = gmp_response.content.metadata
                    if metadata.get("uses_gmp"):
                        if "cross_chain_swap" in str(metadata.get("operation_type", "")):
                            gmp_response.agent_type = AgentType.CROSS_CHAIN_SWAP
                        else:
                            gmp_response.agent_type = AgentType.GMP_OPERATION
                
                return gmp_response
            
            # If it's a different format, convert it
            return UnifiedResponse(
                content={
                    "message": str(gmp_response),
                    "type": "gmp_response"
                },
                agent_type=AgentType.GMP_OPERATION,
                status="success"
            )
            
        except Exception as e:
            logger.exception(f"Error converting GMP response: {e}")
            return UnifiedResponse(
                content={
                    "message": "Cross-chain operation completed, but response formatting failed",
                    "type": "gmp_response"
                },
                agent_type=AgentType.GMP_OPERATION,
                status="success"
            )

    async def _process_transaction_step_complete(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process transaction step completion and return next step if available.

        This handler manages multi-step transaction flows by:
        1. Completing the current step
        2. Advancing to the next step
        3. Returning the next transaction data or completion status
        """
        try:
            if not self.transaction_flow_service:
                raise BusinessLogicError(
                    "Transaction flow service not available",
                    suggestions=["Check service configuration"]
                )

            # Extract step completion data from command details
            step_data = unified_command.details
            if not step_data:
                raise ValidationError("Missing transaction step completion data")

            wallet_address = step_data.get('wallet_address') or unified_command.wallet_address
            chain_id = step_data.get('chain_id') or unified_command.chain_id
            tx_hash = step_data.get('tx_hash')
            success = step_data.get('success', True)
            error = step_data.get('error')

            if not wallet_address or not tx_hash:
                raise ValidationError("Missing required fields: wallet_address and tx_hash")

            logger.info(f"Completing transaction step for {wallet_address}, tx: {tx_hash}")

            # Complete the current step
            step_completed = self.transaction_flow_service.complete_step(
                wallet_address=wallet_address,
                tx_hash=tx_hash,
                success=success,
                error=error
            )

            if not step_completed:
                return UnifiedResponse(
                    content={
                        "message": "No active transaction flow found",
                        "type": "error",
                        "has_next_step": False
                    },
                    agent_type=AgentType.DEFAULT,
                    status="error",
                    error="Failed to complete transaction step - no active flow found"
                )

            # Get the next step if available
            next_step = self.transaction_flow_service.get_next_step(wallet_address)

            if next_step:
                # There's a next step - return it
                transaction_data = TransactionData(
                    to=next_step.to,
                    data=next_step.data,
                    value=next_step.value,
                    gas_limit=next_step.gas_limit,
                    chain_id=chain_id
                )

                current_flow = self.transaction_flow_service.get_current_flow(wallet_address)

                return UnifiedResponse(
                    content={
                        "message": next_step.description,
                        "type": "transaction_step",
                        "has_next_step": True,
                        "flow_info": {
                            "current_step": next_step.step_number,
                            "step_type": next_step.step_type.value,
                            "total_steps": len(current_flow.steps) if current_flow else 1
                        }
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success",
                    awaiting_confirmation=True,
                    transaction=transaction_data.model_dump() if hasattr(transaction_data, 'model_dump') else transaction_data.__dict__
                )
            else:
                # No more steps - flow is complete
                return UnifiedResponse(
                    content={
                        "message": "Transaction flow completed successfully",
                        "type": "completion",
                        "has_next_step": False
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success"
                )

        except ValidationError as e:
            logger.error(f"Validation error in transaction step completion: {e}")
            return UnifiedResponse(
                content={
                    "message": f"Invalid transaction step data: {str(e)}",
                    "type": "error",
                    "has_next_step": False
                },
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Error processing transaction step completion: {e}")
            return UnifiedResponse(
                content={
                    "message": "Failed to process transaction step completion",
                    "type": "error",
                    "has_next_step": False
                },
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e)
            )
