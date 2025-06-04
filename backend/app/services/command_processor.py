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
- CONTEXTUAL_QUESTION: Questions about previously discussed topics (like "what did you learn?", "tell me more", "what are the risks?")
- PROTOCOL_RESEARCH: Research requests about DeFi protocols
- TRANSFER: Token transfer requests
- BRIDGE: Cross-chain bridge requests
- SWAP: Token swap requests
- BALANCE: Balance check requests
- PORTFOLIO: Portfolio analysis requests
- GREETING: Greetings and casual conversation
- CONFIRMATION: Yes/no confirmations
- UNKNOWN: Unclear or unrelated commands

Respond with ONLY the command type name (e.g., "CONTEXTUAL_QUESTION").

If the user is asking about something that was recently discussed (like a protocol that was just researched), classify it as CONTEXTUAL_QUESTION.
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
        # Awareness triggers
        about_triggers = [
            "who are you", "what are you", "what can you do", "about you", "about snel", "your purpose", "what is snel", "describe yourself"
        ]
        cmd_lower = unified_command.command.lower().strip()
        if any(trigger in cmd_lower for trigger in about_triggers):
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
        response_text = greeting_responses.get(cmd_lower, "Hello! How can I help you with crypto today?")

        return UnifiedResponse(
            content={
                "message": response_text,
                "type": "greeting"
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

            if not context:
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

            prompt = f"""
You are SNEL, a helpful DeFi assistant. Answer the user's question based on the recent conversation context.

RECENT CONVERSATION CONTEXT:
{context}

USER QUESTION: "{unified_command.command}"

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
