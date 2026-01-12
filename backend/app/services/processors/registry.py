"""
Processor registry for command routing.
Maps command types to their respective processors.
"""
from typing import Dict, Type
from ...models.unified_models import CommandType
from .base_processor import BaseProcessor
from .swap_processor import SwapProcessor
from .bridge_processor import BridgeProcessor, PrivacyBridgeProcessor
from .transfer_processor import TransferProcessor
from .balance_processor import BalanceProcessor
from .portfolio_processor import PortfolioProcessor
from .contextual_processor import ContextualProcessor
from .protocol_processor import ProtocolProcessor
from .privacy_processor import PrivacyProcessor
from .payment_action_processor import PaymentActionProcessor
from .x402_processor import X402Processor


class ProcessorRegistry:
    """Registry for mapping command types to processors."""
    
    def __init__(self, brian_client=None, settings=None, protocol_registry=None, gmp_service=None, price_service=None, transaction_flow_service=None):
        """Initialize registry with shared dependencies."""
        # Note: brian_client param kept for backward compatibility but not used
        self.dependencies = {
            'settings': settings,
            'protocol_registry': protocol_registry,
            'gmp_service': gmp_service,
            'price_service': price_service,
            'transaction_flow_service': transaction_flow_service,
        }
        
        # Initialize processors
        self._processors: Dict[CommandType, BaseProcessor] = {
            # Transaction processors
            CommandType.SWAP: SwapProcessor(**self.dependencies),
            CommandType.BRIDGE: BridgeProcessor(**self.dependencies),
            CommandType.BRIDGE_TO_PRIVACY: PrivacyBridgeProcessor(**self.dependencies),
            CommandType.TRANSFER: TransferProcessor(**self.dependencies),
            CommandType.CROSS_CHAIN_SWAP: SwapProcessor(**self.dependencies),
            
            # Privacy processors
            CommandType.SET_PRIVACY_DEFAULT: PrivacyProcessor(**self.dependencies),
            CommandType.OVERRIDE_PRIVACY: PrivacyProcessor(**self.dependencies),
            CommandType.X402_PRIVACY: PrivacyProcessor(**self.dependencies),
            
            # X402 agentic payment processors
            CommandType.X402_PAYMENT: X402Processor(**self.dependencies),
            
            # Payment action processors
            CommandType.PAYMENT_ACTION: PaymentActionProcessor(**self.dependencies),
            
            # Query processors
            CommandType.BALANCE: BalanceProcessor(**self.dependencies),
            CommandType.PORTFOLIO: PortfolioProcessor(**self.dependencies),
            CommandType.PROTOCOL_RESEARCH: ProtocolProcessor(**self.dependencies),
            
            # Contextual processors
            CommandType.GREETING: ContextualProcessor(**self.dependencies),
            CommandType.CONTEXTUAL_QUESTION: ContextualProcessor(**self.dependencies),
        }
    
    def get_processor(self, command_type: CommandType) -> BaseProcessor:
        """
        Get processor for command type.
        
        Args:
            command_type: The type of command to process
            
        Returns:
            Processor instance for the command type
            
        Raises:
            KeyError: If no processor exists for the command type
        """
        processor = self._processors.get(command_type)
        if not processor:
            raise KeyError(f"No processor registered for {command_type}")
        return processor
    
    def register_processor(self, command_type: CommandType, processor_class: Type[BaseProcessor]):
        """
        Register a new processor for a command type.
        
        Args:
            command_type: The command type to register
            processor_class: The processor class to instantiate
        """
        self._processors[command_type] = processor_class(**self.dependencies)
    
    def has_processor(self, command_type: CommandType) -> bool:
        """Check if a processor exists for the command type."""
        return command_type in self._processors