"""
Base processor class for command processing.
Provides common functionality for all domain processors.
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, TransactionData, CommandType
)
from app.core.exceptions import BusinessLogicError
from app.services.utils.transaction_utils import transaction_utils
from app.services.error_guidance_service import error_guidance_service, ErrorContext


class BaseProcessor(ABC):
    """Base class for all command processors."""
    
    def __init__(self, settings, protocol_registry, gmp_service, price_service):
        """
        Initialize base processor with shared dependencies.
        
        Args:
            settings: Application settings
            protocol_registry: Protocol registry for cross-chain operations
            gmp_service: Axelar GMP service
            price_service: Price service for USD conversions
        """
        self.settings = settings
        self.protocol_registry = protocol_registry
        self.gmp_service = gmp_service
        self.price_service = price_service
    
    @abstractmethod
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process the command and return a unified response.
        
        Args:
            unified_command: The command to process
            
        Returns:
            UnifiedResponse with the result
        """
        pass
    
    def _format_amount(self, amount: float) -> str:
        """
        Format amount to avoid scientific notation.
        Uses shared utility for consistency across codebase.
        """
        return transaction_utils.format_amount(amount)
    
    def _create_transaction_data(self, result: dict, chain_id: int) -> Optional[TransactionData]:
        """
        Create transaction data from API result.
        Uses shared utility to handle various response formats consistently.
        """
        return transaction_utils.create_transaction_data(result, chain_id)
    
    def _create_error_response(
        self,
        message: str,
        agent_type: AgentType = AgentType.DEFAULT,
        error: Optional[str] = None
    ) -> UnifiedResponse:
        """Create a standardized error response."""
        return UnifiedResponse(
            content={"message": message, "type": "error"},
            agent_type=agent_type,
            status="error",
            error=error or message
        )
    
    def _create_guided_error_response(
        self,
        command_type: CommandType,
        agent_type: AgentType,
        error_context: ErrorContext,
        missing_params: Optional[list] = None,
        additional_message: Optional[str] = None,
        error: Optional[str] = None
    ) -> UnifiedResponse:
        """
        Create an error response with contextual guidance.
        Uses the centralized error guidance service for consistent messaging.
        
        This is the preferred method for generating error responses as it ensures
        users always get helpful guidance, not just error messages.
        """
        return error_guidance_service.create_error_response(
            command_type=command_type,
            agent_type=agent_type,
            error_context=error_context,
            missing_params=missing_params,
            additional_message=additional_message,
            error=error
        )
    
    def _create_success_response(
        self,
        content: Dict[str, Any],
        agent_type: AgentType,
        transaction: Optional[TransactionData] = None,
        awaiting_confirmation: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UnifiedResponse:
        """Create a standardized success response."""
        return UnifiedResponse(
            content=content,
            agent_type=agent_type,
            status="success",
            transaction=transaction,
            awaiting_confirmation=awaiting_confirmation,
            metadata=metadata or {}
        )
