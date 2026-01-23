"""
Balance command processor.
Handles balance check operations.
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.exceptions import wallet_not_connected_error
from ...models.unified_models import AgentType, UnifiedCommand, UnifiedResponse
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

            # Validate wallet connection and chain
            if not unified_command.wallet_address:
                raise wallet_not_connected_error()

            chain_id: int = (
                unified_command.chain_id or 1
            )  # Default to Ethereum if not specified

            # Get chain name for display
            chain_name: str = self.settings.chains.supported_chains.get(
                chain_id, f"Chain {chain_id}"
            )

            logger.info(
                f"Checking balance for {unified_command.wallet_address} on {chain_name}"
            )
            if token:
                logger.info(f"Specific token requested: {token}")

            # Get balances via TokenQueryService (consolidates Web3 operations)
            from ..token_query_service import token_query_service

            balances: dict[str, Any] = await token_query_service.get_balances(
                wallet_address=unified_command.wallet_address,
                chain_id=chain_id,
            )

            # Determine display token and balance data for frontend
            display_token = token if token else "All tokens"

            # Prepare primary balance data for display (string format for UI)
            balance_data: str
            if token:
                token_upper = token.upper()
                token_bal = balances.get("token_balances", {}).get(token_upper)
                if token_bal is not None:
                    balance_data = f"{token_bal} {token_upper}"
                else:
                    # Check if it's the native token
                    native_bal = balances.get("native_balance", 0)
                    balance_data = f"{native_bal} {token_upper}"
            else:
                # Summary for all tokens
                from ...config.tokens import COMMON_TOKENS

                # Identify native symbol (default to ETH)
                native_symbol = "ETH"
                chain_tokens = COMMON_TOKENS.get(chain_id, {})
                for sym, info in chain_tokens.items():
                    if (
                        info.get("address")
                        == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                    ):
                        native_symbol = sym.upper()
                        break

                native_bal = balances.get("native_balance", 0)
                summary_parts = [f"{native_bal} {native_symbol}"]

                # Add other non-zero balances
                token_balances: dict[str, float] = balances.get("token_balances", {})
                for sym, bal in token_balances.items():
                    if bal > 0 and sym.upper() != native_symbol:
                        summary_parts.append(f"{bal} {sym.upper()}")

                balance_data = "\n".join(summary_parts)

            # Format successful balance response
            content = {
                "message": f"Balance check complete for {chain_name}",
                "type": "balance_result",
                "chain": chain_name,
                "address": unified_command.wallet_address,
                "token": display_token,
                "balance_data": balance_data,
                "native_balance": balances.get("native_balance"),
                "token_balances": balances.get("token_balances"),
                "requires_transaction": False,
            }

            return self._create_success_response(
                content=content,
                agent_type=AgentType.BALANCE,
                metadata={
                    "parsed_command": {
                        "token": token,
                        "chain": chain_name,
                        "command_type": "balance",
                    },
                    "balance_details": {
                        "chain_id": chain_id,
                        "wallet_address": unified_command.wallet_address,
                        "token_filter": token,
                    },
                },
            )

        except Exception as e:
            logger.exception("Error processing balance command")
            return self._create_error_response(
                "Failed to check balance", AgentType.BALANCE, str(e)
            )
