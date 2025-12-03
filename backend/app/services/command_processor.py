"""
Unified command processor orchestrator.
Routes commands to domain-specific processors via the registry pattern.
Clean separation of concerns - orchestration vs. command handling.
"""
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.models.unified_models import (
    CommandType, UnifiedCommand, UnifiedResponse, AgentType
)
from app.core.parser.unified_parser import unified_parser
from app.config.settings import Settings
from app.services.chat_history import chat_history_service
from app.core.exceptions import (
    ValidationError, 
    BusinessLogicError, 
    ExternalServiceError,
    wallet_not_connected_error,
    unsupported_chain_error
)
from app.services.processors.registry import ProcessorRegistry

logger = logging.getLogger(__name__)


class CommandProcessor:
    """
    Unified command processor - orchestrator for domain-specific processors.
    
    Responsibilities:
    - Command parsing and validation
    - Command type detection (including AI classification)
    - Routing to appropriate domain processor
    - Consistent error handling
    - Response formatting
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
        
        # Import protocol registry for cross-chain support
        from app.protocols.registry import protocol_registry
        self.protocol_registry = protocol_registry
        
        # Import GMP service for advanced cross-chain operations
        from app.services.axelar_gmp_service import axelar_gmp_service
        self.gmp_service = axelar_gmp_service
        
        # Import enhanced cross-chain handler for GMP operations
        from app.services.enhanced_crosschain_handler import enhanced_crosschain_handler
        self.gmp_handler = enhanced_crosschain_handler
        
        # Import price service for USD to token conversions
        from app.services.price_service import price_service
        self.price_service = price_service
        
        # Initialize processor registry with shared dependencies
        self.processor_registry = ProcessorRegistry(
            brian_client=brian_client,
            settings=settings,
            protocol_registry=self.protocol_registry,
            gmp_service=self.gmp_service,
            price_service=price_service
        )

    @staticmethod
    def create_unified_command(
        command: str,
        wallet_address: str = None,
        chain_id: int = None,
        user_name: str = None,
        openai_api_key: str = None
    ) -> UnifiedCommand:
        """Create a unified command using the unified parser."""
        return unified_parser.create_unified_command(
            command=command,
            wallet_address=wallet_address,
            chain_id=chain_id,
            user_name=user_name,
            openai_api_key=openai_api_key
        )

    @staticmethod
    def validate_command(unified_command: UnifiedCommand):
        """Validate a unified command."""
        return unified_parser.validate_command(unified_command)
    
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
- CONTEXTUAL_QUESTION: Questions about previously discussed topics, about you (the assistant), your capabilities, privacy features, or general crypto/finance topics that require knowledge and reasoning
- PROTOCOL_RESEARCH: Research requests about DeFi protocols
- TRANSFER: Token transfer requests
- BRIDGE: Cross-chain bridge requests
- SWAP: Token swap requests (same chain)
- CROSS_CHAIN_SWAP: Advanced cross-chain swaps using Axelar GMP
- GMP_OPERATION: General Message Passing operations like cross-chain contract calls
- BALANCE: Balance check requests
- PORTFOLIO: Portfolio analysis requests
- BRIDGE_TO_PRIVACY: Requests to bridge to Zcash or use privacy pools (questions about making funds private)
- GREETING: Only simple greetings like "hi", "hello", "hey", without other content
- CONFIRMATION: Yes/no confirmations
- UNKNOWN: Unclear or unrelated commands

Classification guidelines:
- Questions about who you are, what you can do, privacy features → CONTEXTUAL_QUESTION (not GREETING)
- Questions that require explanations or detailed responses → CONTEXTUAL_QUESTION
- Questions about privacy, making funds private, private transactions → BRIDGE_TO_PRIVACY or CONTEXTUAL_QUESTION (about privacy capabilities)
- Only classify as GREETING if it's a simple hello with no other content
- If the user is asking about something recently discussed → CONTEXTUAL_QUESTION
- Cross-chain swaps with different tokens or chains → CROSS_CHAIN_SWAP
- Complex cross-chain operations (yield farming, liquidity provision across chains) → GMP_OPERATION
- Contract calls on different chains → GMP_OPERATION
- Simple same-chain swaps → SWAP

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
        """
        Process a command by routing to appropriate processor.
        
        Flow:
        1. Classify command if needed (using AI for ambiguous cases)
        2. Validate wallet/chain requirements
        3. Route to domain-specific processor
        4. Handle errors consistently
        """
        try:
            # If command was classified as UNKNOWN, try AI classification
            if unified_command.command_type == CommandType.UNKNOWN:
                ai_classification = await self._classify_with_ai(unified_command)
                if ai_classification != CommandType.UNKNOWN:
                    unified_command.command_type = ai_classification
                    logger.info(f"AI reclassified command as {ai_classification}")

            # Validate wallet connection for transaction commands
            if unified_command.command_type in [
                CommandType.TRANSFER, CommandType.BRIDGE, CommandType.SWAP,
                CommandType.CROSS_CHAIN_SWAP, CommandType.GMP_OPERATION,
                CommandType.BRIDGE_TO_PRIVACY
            ]:
                if not unified_command.wallet_address:
                    raise wallet_not_connected_error()

            # Validate chain support
            if unified_command.chain_id and unified_command.chain_id not in self.settings.chains.supported_chains:
                raise unsupported_chain_error(
                    unified_command.chain_id,
                    list(self.settings.chains.supported_chains.keys())
                )

            # Route to appropriate processor
            command_type = unified_command.command_type
            
            # Handle special cases
            if await self._should_use_gmp_handler(unified_command):
                return await self._process_gmp_operation(unified_command)
            
            # Try to get a processor for this command type
            if self.processor_registry.has_processor(command_type):
                processor = self.processor_registry.get_processor(command_type)
                return await processor.process(unified_command)
            
            # Handle GMP and special operations
            if command_type == CommandType.GMP_OPERATION:
                return await self._process_gmp_operation(unified_command)
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

    async def _should_use_gmp_handler(self, unified_command: UnifiedCommand) -> bool:
        """
        Determine if a command should be handled by the GMP handler.
        This checks for complex cross-chain operations that require GMP.
        """
        try:
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
                    error="Failed to complete transaction step"
                )

            # Get the next step if available
            next_step = self.transaction_flow_service.get_next_step(wallet_address)

            if next_step:
                from app.models.unified_models import TransactionData
                
                logger.info(f"Next step found: type={next_step.step_type.value}")

                # Create transaction data from the step
                transaction_data = TransactionData(
                    to=next_step.to,
                    data=next_step.data,
                    value=next_step.value,
                    gasLimit=next_step.gas_limit,
                    chainId=chain_id
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

    async def _process_unknown(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process unknown commands by providing helpful guidance.
        This ensures users are never left without direction.
        """
        command_lower = unified_command.command.lower()
        
        # Provide contextual suggestions based on keywords in the command
        suggestions = []
        
        # Check for bridge-related keywords and provide bridge guidance
        if any(word in command_lower for word in ['bridge', 'private', 'zcash', 'privacy']):
            suggestions = [
                "Try 'bridge 0.5 eth from base to optimism' for a cross-chain bridge",
                "Try 'bridge 1 usdc to zcash' to bridge to Zcash for privacy",
                "Try 'what are privacy pools?' to learn about private transactions"
            ]
            return UnifiedResponse(
                content={
                    "message": "I can help with bridges and privacy! Please tell me:\n1. How much you want to bridge\n2. Which token\n3. Where you're bridging to (for cross-chain) or 'zcash' (for privacy)",
                    "type": "help",
                    "suggestions": suggestions
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )
        
        # Check for swap-related keywords
        if any(word in command_lower for word in ['swap', 'exchange', 'trade']):
            suggestions = [
                "Try 'swap 1 eth for usdc'",
                "Try 'swap 100 usdc for eth on arbitrum'",
                "Try 'how much usdc for 1 eth?'"
            ]
            return UnifiedResponse(
                content={
                    "message": "I can help with swaps! Please tell me:\n1. How much you want to swap\n2. What token to swap from\n3. What token to swap to",
                    "type": "help",
                    "suggestions": suggestions
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )
        
        # Check for transfer-related keywords
        if any(word in command_lower for word in ['transfer', 'send', 'move']):
            suggestions = [
                "Try 'transfer 0.1 eth to 0x123...'",
                "Try 'send 100 usdc to vitalik.eth'",
                "Try 'transfer 1 eth to my other address'"
            ]
            return UnifiedResponse(
                content={
                    "message": "I can help with transfers! Please tell me:\n1. How much you want to transfer\n2. What token\n3. Where to send it (address or ENS name)",
                    "type": "help",
                    "suggestions": suggestions
                },
                agent_type=AgentType.DEFAULT,
                status="success"
            )
        
        # Default response for truly unknown commands
        return UnifiedResponse(
            content={
                "message": "I'm not sure how to help with that. I can assist with:\n• Swapping tokens\n• Transferring tokens\n• Bridging across chains\n• Checking balances\n• Privacy-preserving bridges\n\nWhat would you like to do?",
                "type": "help",
                "suggestions": [
                    "Try 'swap 1 eth for usdc'",
                    "Try 'transfer 0.1 eth to address'",
                    "Try 'bridge 100 usdc from ethereum to arbitrum'",
                    "Try 'bridge 1 eth to zcash' for private transactions"
                ]
            },
            agent_type=AgentType.DEFAULT,
            status="success"
        )
