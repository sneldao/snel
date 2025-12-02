"""
Balance command processor.
Handles balance check operations.
"""
import logging

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType
)
from app.core.exceptions import wallet_not_connected_error, ExternalServiceError
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class BalanceProcessor(BaseProcessor):
    """Processes balance commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process balance check command.
        
        Handles:
        - Token balance retrieval
        - All-token balance summary
        - Chain-specific balance queries
        """
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
                return self._create_error_response(
                    result.get("message", "Unable to check balance"),
                    AgentType.BALANCE,
                    result.get("message", "Balance check failed")
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
            
            return self._create_success_response(
                content=content,
                agent_type=AgentType.BALANCE,
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
            
        except Exception as e:
            logger.exception("Error processing balance command")
            return self._create_error_response(
                "Failed to check balance",
                AgentType.BALANCE,
                str(e)
            )
