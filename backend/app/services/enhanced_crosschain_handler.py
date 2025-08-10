"""
Enhanced cross-chain command handler with GMP support.
Handles complex cross-chain operations using Axelar's General Message Passing.
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
import re

from app.services.axelar_gmp_service import axelar_gmp_service, CrossChainSwapParams
from app.services.axelar_service import axelar_service
from app.models.unified_models import UnifiedCommand, UnifiedResponse, ResponseContent

logger = logging.getLogger(__name__)

class EnhancedCrossChainHandler:
    """Handler for advanced cross-chain operations using Axelar GMP."""
    
    def __init__(self):
        """Initialize the enhanced cross-chain handler."""
        self.gmp_service = axelar_gmp_service
        self.axelar_service = axelar_service
        
        # Patterns for detecting complex cross-chain operations
        self.cross_chain_swap_patterns = [
            r"swap.*from\s+(\w+).*to\s+(\w+).*on\s+(\w+)",
            r"bridge.*and.*swap.*(\w+).*to.*(\w+)",
            r"cross.chain.*swap.*(\w+).*for.*(\w+)",
            r"move.*(\w+).*from.*(\w+).*to.*(\w+).*and.*swap"
        ]
        
        self.gmp_operation_patterns = [
            r"execute.*on.*(\w+).*chain",
            r"call.*contract.*on.*(\w+)",
            r"trigger.*function.*on.*(\w+)",
            r"cross.chain.*call.*to.*(\w+)"
        ]

    async def can_handle(self, command: UnifiedCommand) -> bool:
        """
        Check if this handler can process the command.
        
        Args:
            command: The unified command to check
            
        Returns:
            True if this handler can process the command
        """
        command_text = command.original_text.lower()
        
        # Check for cross-chain swap patterns
        for pattern in self.cross_chain_swap_patterns:
            if re.search(pattern, command_text):
                return True
        
        # Check for GMP operation patterns
        for pattern in self.gmp_operation_patterns:
            if re.search(pattern, command_text):
                return True
        
        # Check if it's a cross-chain operation with different chains
        if hasattr(command, 'from_chain') and hasattr(command, 'to_chain'):
            if command.from_chain and command.to_chain and command.from_chain != command.to_chain:
                return True
        
        return False

    async def handle_cross_chain_swap(
        self,
        command: UnifiedCommand,
        wallet_address: str
    ) -> UnifiedResponse:
        """
        Handle cross-chain swap operations using GMP.
        
        Args:
            command: The unified command
            wallet_address: User's wallet address
            
        Returns:
            Unified response with transaction data
        """
        try:
            # Extract swap parameters from command
            swap_params = await self._extract_swap_parameters(command)
            
            if not swap_params:
                return UnifiedResponse(
                    success=False,
                    message="Could not parse cross-chain swap parameters",
                    content=ResponseContent(
                        error="Invalid swap parameters",
                        technical_details="Failed to extract source/destination tokens and chains"
                    )
                )

            # Build cross-chain swap transaction using GMP
            result = await self.gmp_service.build_cross_chain_swap_transaction(
                swap_params, wallet_address
            )
            
            if not result.get("success"):
                return UnifiedResponse(
                    success=False,
                    message=result.get("error", "Failed to build cross-chain swap"),
                    content=ResponseContent(
                        error=result.get("error"),
                        technical_details=result.get("technical_details")
                    )
                )

            # Create response with transaction steps
            return UnifiedResponse(
                success=True,
                message=f"Cross-chain swap prepared: {swap_params.amount} {swap_params.source_token} on {swap_params.source_chain} → {swap_params.dest_token} on {swap_params.dest_chain}",
                content=ResponseContent(
                    transaction_data={
                        "type": "cross_chain_swap_gmp",
                        "protocol": "axelar_gmp",
                        "steps": result["steps"],
                        "estimated_gas_fee": result["estimated_gas_fee"],
                        "estimated_cost_usd": result["estimated_cost_usd"],
                        "gateway_address": result["gateway_address"],
                        "gas_service_address": result["gas_service_address"]
                    },
                    metadata={
                        "source_chain": swap_params.source_chain,
                        "dest_chain": swap_params.dest_chain,
                        "source_token": swap_params.source_token,
                        "dest_token": swap_params.dest_token,
                        "amount": str(swap_params.amount),
                        "recipient": swap_params.recipient,
                        "uses_gmp": True,
                        "axelar_powered": True
                    }
                )
            )
            
        except Exception as e:
            logger.exception(f"Error handling cross-chain swap: {e}")
            return UnifiedResponse(
                success=False,
                message="Failed to process cross-chain swap",
                content=ResponseContent(
                    error="Cross-chain swap processing failed",
                    technical_details=str(e)
                )
            )

    async def handle_gmp_operation(
        self,
        command: UnifiedCommand,
        wallet_address: str
    ) -> UnifiedResponse:
        """
        Handle general message passing operations.
        
        Args:
            command: The unified command
            wallet_address: User's wallet address
            
        Returns:
            Unified response with GMP transaction data
        """
        try:
            # Extract GMP parameters from command
            gmp_params = await self._extract_gmp_parameters(command)
            
            if not gmp_params:
                return UnifiedResponse(
                    success=False,
                    message="Could not parse GMP operation parameters",
                    content=ResponseContent(
                        error="Invalid GMP parameters",
                        technical_details="Failed to extract destination chain and contract details"
                    )
                )

            # Build GMP call transaction
            result = await self.gmp_service.build_gmp_call(
                gmp_params, command.chain_id or 1, wallet_address
            )
            
            if not result.get("success"):
                return UnifiedResponse(
                    success=False,
                    message=result.get("error", "Failed to build GMP operation"),
                    content=ResponseContent(
                        error=result.get("error"),
                        technical_details=result.get("technical_details")
                    )
                )

            return UnifiedResponse(
                success=True,
                message=f"GMP operation prepared for {gmp_params.destination_chain}",
                content=ResponseContent(
                    transaction_data={
                        "type": "general_message_passing",
                        "protocol": "axelar_gmp",
                        "destination_chain": gmp_params.destination_chain,
                        "destination_address": gmp_params.destination_address,
                        "payload": gmp_params.payload,
                        "gas_limit": gmp_params.gas_limit,
                        "estimated_gas_fee": result["estimated_gas_fee"],
                        "gateway_address": result["gateway_address"],
                        "gas_service_address": result["gas_service_address"],
                        "transaction": result["transaction"]
                    },
                    metadata={
                        "uses_gmp": True,
                        "axelar_powered": True,
                        "destination_chain": gmp_params.destination_chain
                    }
                )
            )
            
        except Exception as e:
            logger.exception(f"Error handling GMP operation: {e}")
            return UnifiedResponse(
                success=False,
                message="Failed to process GMP operation",
                content=ResponseContent(
                    error="GMP operation processing failed",
                    technical_details=str(e)
                )
            )

    async def _extract_swap_parameters(self, command: UnifiedCommand) -> Optional[CrossChainSwapParams]:
        """Extract cross-chain swap parameters from command."""
        try:
            command_text = command.original_text.lower()
            
            # Try to extract parameters using regex patterns
            for pattern in self.cross_chain_swap_patterns:
                match = re.search(pattern, command_text)
                if match:
                    groups = match.groups()
                    
                    # Extract basic parameters (this is simplified - would be more sophisticated)
                    source_token = getattr(command, 'from_token', groups[0] if len(groups) > 0 else 'ETH')
                    dest_token = getattr(command, 'to_token', groups[1] if len(groups) > 1 else 'USDC')
                    amount = getattr(command, 'amount', Decimal('1.0'))
                    source_chain = getattr(command, 'from_chain', 'Ethereum')
                    dest_chain = getattr(command, 'to_chain', 'Polygon')
                    recipient = getattr(command, 'recipient', command.wallet_address or '')
                    
                    return CrossChainSwapParams(
                        source_chain=source_chain,
                        dest_chain=dest_chain,
                        source_token=source_token,
                        dest_token=dest_token,
                        amount=amount,
                        recipient=recipient,
                        slippage=0.01  # 1% default slippage
                    )
            
            return None
            
        except Exception as e:
            logger.exception(f"Error extracting swap parameters: {e}")
            return None

    async def _extract_gmp_parameters(self, command: UnifiedCommand) -> Optional[Any]:
        """Extract GMP parameters from command."""
        try:
            # This would be more sophisticated in a real implementation
            # For now, return a basic structure
            from app.services.axelar_gmp_service import GMPCallData
            
            return GMPCallData(
                destination_chain=getattr(command, 'to_chain', 'Polygon'),
                destination_address=getattr(command, 'contract_address', '0x0000000000000000000000000000000000000000'),
                payload='0x',  # Would be encoded function call
                gas_limit=500000
            )
            
        except Exception as e:
            logger.exception(f"Error extracting GMP parameters: {e}")
            return None

    async def get_supported_operations(self) -> List[str]:
        """Get list of supported cross-chain operations."""
        return [
            "cross_chain_swap",
            "cross_chain_transfer",
            "general_message_passing",
            "cross_chain_contract_call",
            "cross_chain_liquidity_provision",
            "cross_chain_yield_farming"
        ]

    async def get_supported_chains(self) -> List[str]:
        """Get list of supported chains for GMP operations."""
        chain_mappings = self.axelar_service.get_supported_chains()
        return list(chain_mappings.values())

# Global instance
enhanced_crosschain_handler = EnhancedCrossChainHandler()
