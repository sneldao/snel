"""
Privacy command processor.
Handles privacy-related commands including setting defaults, overrides, and x402 privacy transactions.
"""
import logging
from typing import Dict, Any, Optional

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, TransactionData, CommandType, PrivacyLevel
)
from app.core.exceptions import BusinessLogicError
from app.services.error_guidance_service import ErrorContext
from app.services.privacy_service import PrivacyService
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class PrivacyProcessor(BaseProcessor):
    """Processes privacy-related commands."""
    
    def __init__(self, brian_client, settings, protocol_registry, gmp_service, price_service):
        """Initialize privacy processor with shared dependencies."""
        super().__init__(brian_client, settings, protocol_registry, gmp_service, price_service)
        self.privacy_service = PrivacyService(None)
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process privacy command based on command type.
        
        Handles:
        - SET_PRIVACY_DEFAULT: Set user's default privacy level
        - OVERRIDE_PRIVACY: Override privacy for specific transaction
        - X402_PRIVACY: Execute x402 privacy transaction
        - BRIDGE_TO_PRIVACY: Bridge to privacy chain with enhanced routing
        """
        try:
            command_type = unified_command.command_type
            details = unified_command.details
            chain_id = unified_command.chain_id
            
            # Route to appropriate privacy handler
            if command_type == CommandType.SET_PRIVACY_DEFAULT:
                return await self._handle_set_privacy_default(unified_command)
            elif command_type == CommandType.OVERRIDE_PRIVACY:
                return await self._handle_override_privacy(unified_command)
            elif command_type == CommandType.X402_PRIVACY:
                return await self._handle_x402_privacy(unified_command)
            elif command_type == CommandType.BRIDGE_TO_PRIVACY:
                return await self._handle_bridge_to_privacy(unified_command)
            else:
                raise BusinessLogicError(f"Unsupported privacy command type: {command_type}")
                
        except Exception as e:
            logger.exception(f"Error processing privacy command: {e}")
            return self._create_error_response(
                command_type=unified_command.command_type,
                error_message=str(e),
                error_context=ErrorContext.PRIVACY_OPERATION_FAILED
            )
    
    async def _handle_set_privacy_default(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle setting default privacy level."""
        try:
            # Extract privacy level from command details
            privacy_level_str = unified_command.details.extra.get('privacy_level', 'public')
            privacy_level = PrivacyLevel(privacy_level_str.lower())
            
            # Validate privacy level is supported on this chain
            is_valid = await self.privacy_service.validate_privacy_request(
                unified_command.chain_id,
                privacy_level
            )
            
            if not is_valid:
                return self._create_guided_error_response(
                    command_type=CommandType.SET_PRIVACY_DEFAULT,
                    error_context=ErrorContext.PRIVACY_UNSUPPORTED,
                    chain_id=unified_command.chain_id,
                    privacy_level=privacy_level
                )
            
            # In production, this would save to user preferences
            # For now, we'll just return success
            
            return UnifiedResponse(
                success=True,
                message=f"Default privacy level set to {privacy_level.value}",
                command_type=CommandType.SET_PRIVACY_DEFAULT,
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                data={
                    "privacy_level": privacy_level.value,
                    "chain_id": unified_command.chain_id,
                    "supported_methods": await self.privacy_service.get_chain_privacy_options(unified_command.chain_id)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to set privacy default: {e}")
            raise BusinessLogicError(f"Failed to set privacy default: {e}")
    
    async def _handle_override_privacy(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle privacy override for specific transaction."""
        try:
            # Extract privacy level from command details
            privacy_level_str = unified_command.details.extra.get('privacy_level', 'public')
            privacy_level = PrivacyLevel(privacy_level_str.lower())
            
            # Validate privacy level is supported on this chain
            is_valid = await self.privacy_service.validate_privacy_request(
                unified_command.chain_id,
                privacy_level
            )
            
            if not is_valid:
                return self._create_guided_error_response(
                    command_type=CommandType.OVERRIDE_PRIVACY,
                    error_context=ErrorContext.PRIVACY_UNSUPPORTED,
                    chain_id=unified_command.chain_id,
                    privacy_level=privacy_level
                )
            
            # Get optimal privacy route
            route = await self.privacy_service.get_optimal_privacy_route(
                source_chain_id=unified_command.chain_id,
                destination=unified_command.details.to_address or "",
                privacy_level=privacy_level
            )
            
            return UnifiedResponse(
                success=True,
                message=f"Using {route.method} for this transaction",
                command_type=CommandType.OVERRIDE_PRIVACY,
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                data={
                    "privacy_level": privacy_level.value,
                    "method": route.method,
                    "estimated_latency": route.estimated_latency,
                    "capabilities": route.capabilities
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to override privacy: {e}")
            raise BusinessLogicError(f"Failed to override privacy: {e}")
    
    async def _handle_x402_privacy(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle x402 privacy transaction."""
        try:
            # Validate x402 privacy is supported on this chain
            capabilities = await self.privacy_service.get_chain_privacy_options(unified_command.chain_id)
            x402_available = any(opt["value"] == "private" and "x402" in opt["label"].lower() for opt in capabilities)
            
            if not x402_available:
                return self._create_guided_error_response(
                    command_type=CommandType.X402_PRIVACY,
                    error_context=ErrorContext.X402_UNAVAILABLE,
                    chain_id=unified_command.chain_id
                )
            
            # Get optimal x402 privacy route
            route = await self.privacy_service.get_optimal_privacy_route(
                source_chain_id=unified_command.chain_id,
                destination=unified_command.details.to_address or "",
                privacy_level=PrivacyLevel.PRIVATE
            )
            
            # In production, this would initiate the x402 transaction
            # For now, we'll return the route information
            
            return UnifiedResponse(
                success=True,
                message=f"x402 privacy transaction prepared using {route.method}",
                command_type=CommandType.X402_PRIVACY,
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                data={
                    "method": route.method,
                    "estimated_latency": route.estimated_latency,
                    "capabilities": route.capabilities,
                    "next_steps": [
                        "Review privacy transaction details",
                        "Confirm transaction",
                        "Monitor privacy settlement"
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to process x402 privacy: {e}")
            raise BusinessLogicError(f"Failed to process x402 privacy: {e}")
    
    async def _handle_bridge_to_privacy(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle bridge to privacy with enhanced x402 routing."""
        try:
            # This extends the existing bridge processor with x402 capabilities
            # Get the optimal privacy route
            route = await self.privacy_service.get_optimal_privacy_route(
                source_chain_id=unified_command.chain_id,
                destination=unified_command.details.to_address or "zcash:",
                privacy_level=PrivacyLevel.PRIVATE
            )
            
            return UnifiedResponse(
                success=True,
                message=f"Privacy bridge prepared using {route.method}",
                command_type=CommandType.BRIDGE_TO_PRIVACY,
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                data={
                    "method": route.method,
                    "estimated_latency": route.estimated_latency,
                    "capabilities": route.capabilities,
                    "privacy_guarantees": [
                        "Transaction details hidden on blockchain",
                        "Shielded addresses protect sender and receiver",
                        "Compliance records available if needed"
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to bridge to privacy: {e}")
            raise BusinessLogicError(f"Failed to bridge to privacy: {e}")
    
    async def _create_guided_error_response(
        self,
        command_type: CommandType,
        error_context: ErrorContext,
        **kwargs
    ) -> UnifiedResponse:
        """Create guided error response for privacy operations."""
        chain_id = kwargs.get('chain_id')
        privacy_level = kwargs.get('privacy_level', PrivacyLevel.PRIVATE)
        
        # Get chain-specific guidance
        if error_context == ErrorContext.PRIVACY_UNSUPPORTED:
            capabilities = await self.privacy_service.get_chain_privacy_options(chain_id)
            available_options = [opt["label"] for opt in capabilities]
            
            return UnifiedResponse(
                success=False,
                message=f"{privacy_level.value} privacy not supported on this chain",
                command_type=command_type,
                agent_type=AgentType.ERROR,
                data={
                    "error": "privacy_unsupported",
                    "available_options": available_options,
                    "suggestion": f"Try one of: {', '.join(available_options)}"
                }
            )
        
        elif error_context == ErrorContext.X402_UNAVAILABLE:
            return UnifiedResponse(
                success=False,
                message="x402 privacy not available on this chain",
                command_type=command_type,
                agent_type=AgentType.ERROR,
                data={
                    "error": "x402_unavailable",
                    "suggestion": "Try regular privacy or switch to a supported chain"
                }
            )
        
        else:
            return self._create_error_response(
                command_type=command_type,
                error_message="Privacy operation failed",
                error_context=error_context
            )