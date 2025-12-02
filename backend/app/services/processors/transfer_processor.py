"""
Transfer command processor.
Handles token transfer operations.
"""
import logging
from typing import Optional

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType
)
from app.core.exceptions import (
    command_parse_error, invalid_amount_error, ExternalServiceError
)
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class TransferProcessor(BaseProcessor):
    """Processes transfer commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process transfer command.
        
        Handles:
        - Token transfer validation
        - Destination address resolution
        - Transaction preparation
        """
        try:
            logger.info(f"Processing transfer command: {unified_command.command}")
            
            # Extract transfer details
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
                    "protocol": result.get("protocol", {})
                }
            )
            
        except Exception as e:
            logger.exception("Error processing transfer command")
            return self._create_error_response(
                f"Transfer failed: {str(e)}",
                AgentType.TRANSFER,
                str(e)
            )
