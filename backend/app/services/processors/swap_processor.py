"""
Swap command processor.
Handles all swap-related operations.
"""
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, TransactionData, CommandType
)
from app.core.exceptions import BusinessLogicError, invalid_amount_error
from app.services.error_guidance_service import ErrorContext
from app.services.utils.transaction_utils import transaction_utils
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class SwapProcessor(BaseProcessor):
    """Processes swap commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process swap command.
        
        Handles:
        - Token normalization (ETH -> WETH)
        - USD to token amount conversion
        - Protocol selection (0x, Uniswap, etc.)
        - Multi-step approval flows
        """
        try:
            details = unified_command.details
            
            # Extract swap parameters
            token_in = details.token_in.symbol if details.token_in else None
            token_out = details.token_out.symbol if details.token_out else None
            amount = details.amount
            chain_id = unified_command.chain_id
            
            # Check for missing parameters
            missing_params = []
            if not token_in:
                missing_params.append("token_in")
            if not token_out:
                missing_params.append("token_out")
            if not amount:
                missing_params.append("amount")
            if not chain_id:
                missing_params.append("chain")
            
            if missing_params:
                # Use centralized error guidance for consistent messaging
                error_context = ErrorContext.MISSING_AMOUNT if not amount else \
                               ErrorContext.MISSING_TOKEN_PAIR if not (token_in and token_out) else \
                               ErrorContext.MISSING_CHAIN
                return self._create_guided_error_response(
                    command_type=CommandType.SWAP,
                    agent_type=AgentType.SWAP,
                    error_context=error_context,
                    missing_params=missing_params
                )
            
            # Normalize tokens for DEX compatibility
            token_in = self._normalize_token_for_swap(token_in, chain_id)
            token_out = self._normalize_token_for_swap(token_out, chain_id)
            
            # Convert USD amounts if needed
            if details.is_usd_amount:
                amount = await self._convert_usd_to_token(amount, token_in, chain_id)
            
            # Get swap quote from protocol registry
            quote = await self._get_best_swap_quote(
                token_in, token_out, amount, chain_id
            )
            
            if not quote:
                return self._create_guided_error_response(
                    command_type=CommandType.SWAP,
                    agent_type=AgentType.SWAP,
                    error_context=ErrorContext.NO_LIQUIDITY,
                    additional_message=f"No swap route found for {token_in} -> {token_out} on this chain."
                )
            
            # Check if approval is needed
            if quote.get("needs_approval"):
                return await self._create_approval_flow(
                    unified_command, quote, details, amount
                )
            
            # Create transaction data
            transaction = self._create_transaction_data(quote, chain_id)
            
            return self._create_success_response(
                content={
                    "message": f"Ready to swap {amount} {token_in} for {token_out}",
                    "type": "swap_ready",
                    "details": {
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount": str(amount),
                        "estimated_output": quote.get("buyAmount"),
                        "protocol": quote.get("protocol", "0x"),
                        "price_impact": quote.get("priceImpact"),
                    }
                },
                agent_type=AgentType.SWAP,
                transaction=transaction,
                awaiting_confirmation=True,
                metadata={
                    "quote": quote,
                    "token_in": token_in,
                    "token_out": token_out,
                }
            )
            
        except Exception as e:
            logger.exception(f"Error processing swap: {e}")
            return self._create_guided_error_response(
                command_type=CommandType.SWAP,
                agent_type=AgentType.SWAP,
                error_context=ErrorContext.GENERIC_FAILURE,
                error=str(e),
                additional_message=f"Swap processing failed: {str(e)}"
            )
    
    def _normalize_token_for_swap(self, token_symbol: str, chain_id: int) -> str:
        """
        Normalize token symbols for DEX compatibility.
        
        Users often say "ETH" when they mean the native token, but DEX protocols
        typically need "WETH" (Wrapped ETH) for swaps.
        """
        # Native token mappings
        native_to_wrapped = {
            "ETH": "WETH",
            "MATIC": "WMATIC",
            "BNB": "WBNB",
            "AVAX": "WAVAX",
        }
        
        # Check if this is a native token that needs wrapping
        if token_symbol.upper() in native_to_wrapped:
            return native_to_wrapped[token_symbol.upper()]
        
        return token_symbol.upper()
    
    async def _convert_usd_to_token(
        self, usd_amount: Decimal, token_symbol: str, chain_id: int
    ) -> Decimal:
        """Convert USD amount to token amount using price service."""
        try:
            token_price = await self.price_service.get_token_price(token_symbol, chain_id)
            if not token_price or token_price == 0:
                raise BusinessLogicError(f"Could not fetch price for {token_symbol}")
            
            token_amount = usd_amount / Decimal(str(token_price))
            return token_amount
            
        except Exception as e:
            logger.error(f"USD conversion failed: {e}")
            raise invalid_amount_error(f"Could not convert ${usd_amount} to {token_symbol}")
    
    async def _get_best_swap_quote(
        self, token_in: str, token_out: str, amount: Decimal, chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get best swap quote from available protocols."""
        try:
            # Try protocol registry first (supports multiple DEXs)
            quote = await self.protocol_registry.get_swap_quote(
                token_in=token_in,
                token_out=token_out,
                amount=str(amount),
                chain_id=chain_id
            )
            
            if quote:
                return quote
            
            # Fallback to Brian API
            result = await self.brian_client.get_swap_quote(
                token_in=token_in,
                token_out=token_out,
                amount=str(amount),
                chain_id=chain_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get swap quote: {e}")
            return None
    
    async def _create_approval_flow(
        self,
        unified_command: UnifiedCommand,
        quote: Dict[str, Any],
        details: Any,
        amount: Decimal
    ) -> UnifiedResponse:
        """Create a multi-step transaction flow with approval + swap."""
        try:
            token_address = quote.get("token_in_address")
            spender = quote.get("spender") or quote.get("to")
            
            if not token_address or not spender:
                return self._create_error_response(
                    "Missing approval parameters",
                    AgentType.SWAP
                )
            
            # Create approval transaction
            approval_tx = TransactionData(
                to=token_address,
                data=self._encode_approval(spender, amount),
                value="0",
                chain_id=unified_command.chain_id,
                gas_limit="100000"
            )
            
            return self._create_success_response(
                content={
                    "message": f"Approval required for {details.token_in.symbol}",
                    "type": "swap_approval",
                    "flow_info": {
                        "current_step": 1,
                        "total_steps": 2,
                        "step_type": "approval"
                    }
                },
                agent_type=AgentType.SWAP,
                transaction=approval_tx,
                awaiting_confirmation=True,
                metadata={"quote": quote, "next_step": "swap"}
            )
            
        except Exception as e:
            logger.exception(f"Failed to create approval flow: {e}")
            return self._create_error_response(
                f"Approval flow creation failed: {str(e)}",
                AgentType.SWAP
            )
    
    def _encode_approval(self, spender: str, amount: Decimal) -> str:
        """
        Encode ERC20 approval function call.
        Uses shared utility to ensure consistency across codebase.
        """
        return transaction_utils.encode_erc20_approval(spender, amount)
