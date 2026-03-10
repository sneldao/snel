"""
Privacy command processor.
Handles privacy-related commands including setting defaults, overrides, and x402 privacy transactions.
Enhanced for Starknet-native ZK privacy.
"""
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, TransactionData, CommandType, PrivacyLevel, ResponseContent
)
from app.core.exceptions import BusinessLogicError
from app.services.error_guidance_service import ErrorContext
from app.services.privacy_service import PrivacyService
from app.services.starknet_service import starknet_service
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class PrivacyProcessor(BaseProcessor):
    """Processes privacy-related commands."""
    
    def __init__(self, settings=None, protocol_registry=None, gmp_service=None, price_service=None, **kwargs):
        """Initialize privacy processor with shared dependencies."""
        super().__init__(settings, protocol_registry, gmp_service, price_service, **kwargs)
        self.privacy_service = PrivacyService(None)
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process privacy command based on command type.
        """
        try:
            command_type = unified_command.command_type
            
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
                message=str(e),
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                error=str(e)
            )
    
    async def _handle_set_privacy_default(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle setting default privacy level."""
        try:
            details = unified_command.details
            privacy_level_str = details.additional_params.get('privacy_level', 'public') if details and details.additional_params else 'public'
            privacy_level = PrivacyLevel(privacy_level_str.lower())
            
            is_valid = await self.privacy_service.validate_privacy_request(
                unified_command.chain_id,
                privacy_level
            )
            
            if not is_valid:
                return self._create_guided_error_response(
                    command_type=CommandType.SET_PRIVACY_DEFAULT,
                    agent_type=AgentType.BRIDGE_TO_PRIVACY,
                    error_context=ErrorContext.PRIVACY_UNSUPPORTED
                )
            
            return self._create_success_response(
                content={
                    "message": f"Default privacy level set to {privacy_level.value}",
                    "type": "privacy_setting_updated"
                },
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                metadata={
                    "privacy_level": privacy_level.value,
                    "chain_id": unified_command.chain_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to set privacy default: {e}")
            raise BusinessLogicError(f"Failed to set privacy default: {e}")
    
    async def _handle_override_privacy(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle privacy override for specific transaction."""
        try:
            details = unified_command.details
            privacy_level_str = details.additional_params.get('privacy_level', 'public') if details and details.additional_params else 'public'
            privacy_level = PrivacyLevel(privacy_level_str.lower())
            
            is_valid = await self.privacy_service.validate_privacy_request(
                unified_command.chain_id,
                privacy_level
            )
            
            if not is_valid:
                return self._create_guided_error_response(
                    command_type=CommandType.OVERRIDE_PRIVACY,
                    agent_type=AgentType.BRIDGE_TO_PRIVACY,
                    error_context=ErrorContext.PRIVACY_UNSUPPORTED
                )
            
            route = await self.privacy_service.get_optimal_privacy_route(
                source_chain_id=unified_command.chain_id,
                destination=details.destination if details else "",
                privacy_level=privacy_level
            )
            
            return self._create_success_response(
                content={
                    "message": f"Using {route.method} for this transaction",
                    "type": "privacy_override_ready"
                },
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                metadata={
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
            capabilities = await self.privacy_service.get_chain_privacy_options(unified_command.chain_id)
            x402_available = any("x402" in opt["label"].lower() for opt in capabilities)
            
            if not x402_available:
                return self._create_guided_error_response(
                    command_type=CommandType.X402_PRIVACY,
                    agent_type=AgentType.BRIDGE_TO_PRIVACY,
                    error_context=ErrorContext.X402_UNAVAILABLE
                )
            
            route = await self.privacy_service.get_optimal_privacy_route(
                source_chain_id=unified_command.chain_id,
                destination=unified_command.details.destination if unified_command.details else "",
                privacy_level=PrivacyLevel.PRIVATE
            )
            
            return self._create_success_response(
                content={
                    "message": f"x402 privacy transaction prepared using {route.method}",
                    "type": "x402_privacy_ready",
                    "next_steps": ["Confirm transaction", "Monitor privacy settlement"]
                },
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                metadata={
                    "method": route.method,
                    "estimated_latency": route.estimated_latency,
                    "capabilities": route.capabilities
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to process x402 privacy: {e}")
            raise BusinessLogicError(f"Failed to process x402 privacy: {e}")
    
    async def _handle_bridge_to_privacy(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle bridge to privacy with enhanced x402 and Starknet routing."""
        try:
            details = unified_command.details
            if not details:
                raise BusinessLogicError("Missing command details for privacy operation")

            additional_params = details.additional_params or {}
            is_shield = additional_params.get("is_shield", False)
            is_unshield = additional_params.get("is_unshield", False)
            
            # Get the optimal privacy route
            route = await self.privacy_service.get_optimal_privacy_route(
                source_chain_id=unified_command.chain_id,
                destination=details.destination_chain or details.destination or "privacy",
                privacy_level=PrivacyLevel.PRIVATE
            )
            
            # Handle Starknet Native Privacy
            if route.method == "starknet_privacy":
                if is_shield:
                    # For demo, generate a mock commitment
                    commitment = f"0x{int(details.amount or 0):064x}"
                    result = starknet_service.build_shield_tx(
                        token_address="0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7", # ETH
                        amount=Decimal(str(details.amount or 0)),
                        commitment=commitment
                    )
                    
                    content = {
                        "message": f"Ready to shield {details.amount} {details.token_in.symbol if details.token_in else 'ETH'} on Starknet",
                        "type": "privacy_shield_ready",
                        "requires_transaction": True,
                        "details": {
                            "amount": str(details.amount),
                            "token": details.token_in.symbol if details.token_in else 'ETH',
                            "method": "Starknet ZK-Shielding"
                        }
                    }
                    
                    tx_data = TransactionData(
                        to=result["contractAddress"],
                        data=str(result["calldata"]), # Calldata is complex for Starknet, stringify for model
                        value="0",
                        chain_id=unified_command.chain_id
                    )
                    
                    return self._create_success_response(
                        content=content,
                        agent_type=AgentType.BRIDGE_TO_PRIVACY,
                        transaction=tx_data,
                        awaiting_confirmation=True,
                        metadata={"starknet_tx": result}
                    )
                
                elif is_unshield:
                    content = {
                        "message": "Ready to unshield assets on Starknet. This will require generating a ZK-proof in your browser.",
                        "type": "privacy_unshield_ready",
                        "requires_transaction": True,
                        "details": {
                            "amount": str(details.amount),
                            "token": details.token_in.symbol if details.token_in else 'ETH',
                            "method": "Starknet ZK-Unshielding"
                        }
                    }
                    return self._create_success_response(
                        content=content,
                        agent_type=AgentType.BRIDGE_TO_PRIVACY,
                        awaiting_confirmation=True
                    )

            # Fallback to standard bridge to privacy (Zcash, etc.)
            return self._create_success_response(
                content={
                    "message": f"Privacy bridge prepared using {route.method}",
                    "type": "privacy_bridge_ready",
                    "details": {
                        "method": route.method,
                        "estimated_latency": route.estimated_latency
                    }
                },
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                metadata={ 
                    "method": route.method,
                    "capabilities": route.capabilities
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to bridge to privacy: {e}")
            raise BusinessLogicError(f"Failed to bridge to privacy: {e}")
