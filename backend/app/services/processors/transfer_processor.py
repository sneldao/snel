"""
Transfer command processor.
Handles token transfer operations with gas optimization suggestions.
"""
import logging
from typing import Optional
from decimal import Decimal

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, CommandType
)
from app.core.exceptions import (
    command_parse_error, invalid_amount_error, ExternalServiceError, BusinessLogicError
)
from app.services.error_guidance_service import ErrorContext
from app.services.knowledge_base import get_protocol_kb
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class TransferProcessor(BaseProcessor):
    """Processes transfer commands with gas optimization hints."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process transfer command.
        
        Handles:
        - Token transfer validation
        - Destination address resolution
        - Transaction preparation
        - Gas optimization suggestions
        """
        try:
            logger.info(f"Processing transfer command: {unified_command.command}")
            
            # Extract transfer details
            details = unified_command.details
            
            # Null-safety check: details must exist
            if details is None:
                return self._create_guided_error_response(
                    command_type=CommandType.TRANSFER,
                    agent_type=AgentType.TRANSFER,
                    error_context=ErrorContext.MISSING_TOKEN,
                    additional_message="Unable to parse transfer command. Please provide token, amount, and destination address."
                )
            
            # Check for KB context if token is missing
            if not details.token_in:
                return self._create_guided_error_response(
                    command_type=CommandType.TRANSFER,
                    agent_type=AgentType.TRANSFER,
                    error_context=ErrorContext.MISSING_TOKEN,
                    additional_message="Which token would you like to transfer?"
                )
            
            if not details.amount or not details.destination:
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
            
            # Build ERC20 transfer transaction via TokenQueryService (consolidates Web3)
            from app.services.token_query_service import token_query_service
            
            # Validate transfer parameters
            is_valid, error_msg = token_query_service.validate_transfer(
                wallet_address=unified_command.wallet_address,
                token_address=details.token_in.get_address(unified_command.chain_id),
                to_address=details.destination,
                amount=Decimal(str(details.amount))
            )
            
            if not is_valid:
                raise BusinessLogicError(error_msg)
            
            # Build transfer transaction
            result = token_query_service.build_transfer_transaction(
                token_address=details.token_in.get_address(unified_command.chain_id),
                to_address=details.destination,
                amount=Decimal(str(details.amount)),
                decimals=details.token_in.decimals,
                chain_id=unified_command.chain_id
            )
            
            # Check if this transfer could benefit from batching
            gas_optimization_hint = self._check_gas_optimization_opportunity(unified_command)
            
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
            
            # Add gas optimization hint if applicable
            if gas_optimization_hint:
                content["gas_optimization_hint"] = gas_optimization_hint
            
            # Format transaction data
            transaction_data = self._create_transaction_data(result, unified_command.chain_id)
            
            return self._create_success_response(
                content=content,
                agent_type=AgentType.TRANSFER,
                transaction=transaction_data,
                awaiting_confirmation=True,
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
                    "protocol": result.get("protocol", {}),
                    "gas_optimized": gas_optimization_hint is not None
                }
            )
            
        except Exception as e:
            logger.exception("Error processing transfer command")
            return self._create_error_response(
                f"Transfer failed: {str(e)}",
                AgentType.TRANSFER,
                str(e)
            )
    
    def _check_gas_optimization_opportunity(self, unified_command: UnifiedCommand) -> Optional[str]:
        """
        Check if this transfer could benefit from batching with other transfers.
        For Scroll and other L2s, suggests batching for gas savings.
        """
        # Get chain information
        chain_id = unified_command.chain_id
        
        # Check if this is a chain that benefits from batching (Scroll, Arbitrum, etc.)
        if chain_id in [534352, 42161, 10, 8453, 324]:  # Scroll, Arbitrum, Optimism, Base, zkSync
            return f"For gas optimization on {self._get_chain_name(chain_id)}, consider batching multiple transfers. You could save up to 40% on gas fees."
        
        return None
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get chain name from chain ID."""
        chain_names = {
            1: "Ethereum",
            534352: "Scroll",
            42161: "Arbitrum",
            10: "Optimism",
            8453: "Base",
            324: "zkSync Era",
            137: "Polygon",
            56: "BSC"
        }
        return chain_names.get(chain_id, f"Chain {chain_id}")