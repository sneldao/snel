"""
Bridge command processor.
Handles cross-chain bridging operations.
"""
import logging
from typing import Dict, Any, Optional

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, TransactionData
)
from app.core.exceptions import BusinessLogicError
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class BridgeProcessor(BaseProcessor):
    """Processes bridge commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process bridge command.
        
        Handles:
        - Cross-chain asset transfers
        - Axelar GMP integration
        - Multi-step bridge flows
        """
        try:
            details = unified_command.details
            
            # Extract bridge parameters
            token = details.token_in.symbol if details.token_in else None
            amount = details.amount
            from_chain = unified_command.chain_id
            to_chain = details.to_chain_id
            
            if not all([token, amount, from_chain, to_chain]):
                return self._create_error_response(
                    "Missing required bridge parameters",
                    AgentType.BRIDGE
                )
            
            # Check if this is a GMP-eligible operation
            if self._should_use_gmp(from_chain, to_chain):
                return await self._process_gmp_bridge(
                    unified_command, token, amount, from_chain, to_chain
                )
            
            # Use standard bridge protocol
            return await self._process_standard_bridge(
                unified_command, token, amount, from_chain, to_chain
            )
            
        except Exception as e:
            logger.exception(f"Error processing bridge: {e}")
            return self._create_error_response(
                f"Bridge processing failed: {str(e)}",
                AgentType.BRIDGE,
                str(e)
            )
    
    def _should_use_gmp(self, from_chain: int, to_chain: int) -> bool:
        """Determine if GMP should be used for this bridge operation."""
        # GMP is preferred for Axelar-supported chains
        axelar_chains = {1, 8453, 42161, 10, 137, 43114, 56}
        return from_chain in axelar_chains and to_chain in axelar_chains
    
    async def _process_gmp_bridge(
        self,
        unified_command: UnifiedCommand,
        token: str,
        amount: Any,
        from_chain: int,
        to_chain: int
    ) -> UnifiedResponse:
        """Process bridge using Axelar GMP."""
        try:
            # Build GMP bridge transaction
            gmp_result = await self.gmp_service.build_cross_chain_swap(
                source_chain_id=from_chain,
                dest_chain_id=to_chain,
                token_in=token,
                token_out=token,  # Same token on destination
                amount=amount,
                wallet_address=unified_command.wallet_address
            )
            
            if not gmp_result.get("success"):
                raise BusinessLogicError(gmp_result.get("error", "GMP bridge failed"))
            
            # Extract transaction steps
            steps = gmp_result.get("steps", [])
            if not steps:
                raise BusinessLogicError("No transaction steps generated")
            
            # Get first step (usually approval or pay gas)
            first_step = steps[0]
            transaction = TransactionData(
                to=first_step.get("to"),
                data=first_step.get("data"),
                value=first_step.get("value", "0"),
                chain_id=from_chain,
                gas_limit=first_step.get("gas_limit", "500000")
            )
            
            return self._create_success_response(
                content={
                    "message": f"Ready to bridge {amount} {token} via Axelar",
                    "type": "bridge_ready",
                    "flow_info": {
                        "current_step": 1,
                        "total_steps": len(steps),
                        "step_type": first_step.get("type", "approval")
                    },
                    "details": {
                        "token": token,
                        "amount": str(amount),
                        "from_chain": from_chain,
                        "to_chain": to_chain,
                        "protocol": "Axelar GMP",
                        "estimated_time": gmp_result.get("estimated_time", "5-10 minutes")
                    }
                },
                agent_type=AgentType.BRIDGE,
                transaction=transaction,
                awaiting_confirmation=True,
                metadata={
                    "gmp_result": gmp_result,
                    "all_steps": steps,
                    "axelar_powered": True
                }
            )
            
        except Exception as e:
            logger.exception(f"GMP bridge failed: {e}")
            # Fallback to standard bridge
            return await self._process_standard_bridge(
                unified_command, token, amount, from_chain, to_chain
            )
    
    async def _process_standard_bridge(
        self,
        unified_command: UnifiedCommand,
        token: str,
        amount: Any,
        from_chain: int,
        to_chain: int
    ) -> UnifiedResponse:
        """Process bridge using standard protocols (Brian API)."""
        try:
            # Use Brian API for bridge
            result = await self.brian_client.get_bridge_quote(
                token=token,
                amount=str(amount),
                from_chain=from_chain,
                to_chain=to_chain,
                wallet_address=unified_command.wallet_address
            )
            
            if not result or not result.get("success"):
                raise BusinessLogicError("No bridge route found")
            
            transaction = self._create_transaction_data(result, from_chain)
            
            return self._create_success_response(
                content={
                    "message": f"Ready to bridge {amount} {token}",
                    "type": "bridge_ready",
                    "details": {
                        "token": token,
                        "amount": str(amount),
                        "from_chain": from_chain,
                        "to_chain": to_chain,
                        "protocol": result.get("protocol", "Brian"),
                        "estimated_time": result.get("estimated_time", "10-20 minutes")
                    }
                },
                agent_type=AgentType.BRIDGE,
                transaction=transaction,
                awaiting_confirmation=True,
                metadata={"bridge_result": result}
            )
            
        except Exception as e:
            logger.exception(f"Standard bridge failed: {e}")
            return self._create_error_response(
                f"Bridge failed: {str(e)}",
                AgentType.BRIDGE
            )


class PrivacyBridgeProcessor(BaseProcessor):
    """Processes privacy bridge commands (e.g., bridge to Zcash)."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process privacy bridge command.
        
        Handles bridging to privacy-preserving chains like Zcash.
        """
        try:
            details = unified_command.details
            
            # Extract parameters
            token = details.token_in.symbol if details.token_in else None
            amount = details.amount
            from_chain = unified_command.chain_id
            
            if not all([token, amount, from_chain]):
                return self._create_error_response(
                    "Missing required parameters for privacy bridge",
                    AgentType.BRIDGE_TO_PRIVACY
                )
            
            # Build privacy bridge transaction using GMP
            gmp_result = await self.gmp_service.build_bridge_to_privacy_transaction(
                source_chain_id=from_chain,
                token_symbol=token,
                amount=amount,
                wallet_address=unified_command.wallet_address
            )
            
            if not gmp_result.get("success"):
                raise BusinessLogicError(gmp_result.get("error", "Privacy bridge failed"))
            
            # Extract transaction steps
            steps = gmp_result.get("steps", [])
            first_step = steps[0] if steps else None
            
            if not first_step:
                raise BusinessLogicError("No transaction steps generated")
            
            transaction = TransactionData(
                to=first_step.get("to"),
                data=first_step.get("data"),
                value=first_step.get("value", "0"),
                chain_id=from_chain,
                gas_limit=first_step.get("gas_limit", "500000")
            )
            
            return self._create_success_response(
                content={
                    "message": f"Ready to bridge {amount} {token} to privacy pool",
                    "type": "bridge_privacy_ready",
                    "amount": str(amount),
                    "token": token,
                    "from_chain": self._get_chain_name(from_chain),
                    "to_chain": "Zcash",
                    "protocol": "Axelar GMP",
                    "estimated_time": gmp_result.get("estimated_time", "5-10 minutes"),
                    "privacy_level": "High (Shielded)",
                    "requires_transaction": True,
                    "steps": steps
                },
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                transaction=transaction,
                awaiting_confirmation=True,
                metadata={
                    "gmp_result": gmp_result,
                    "privacy_enabled": True,
                    "axelar_powered": True
                }
            )
            
        except Exception as e:
            logger.exception(f"Privacy bridge failed: {e}")
            return self._create_error_response(
                f"Privacy bridge failed: {str(e)}",
                AgentType.BRIDGE_TO_PRIVACY,
                str(e)
            )
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get human-readable chain name."""
        chain_names = {
            1: "Ethereum",
            8453: "Base",
            42161: "Arbitrum",
            10: "Optimism",
            137: "Polygon",
        }
        return chain_names.get(chain_id, f"Chain {chain_id}")
