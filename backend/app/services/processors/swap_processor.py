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
from app.services.knowledge_base import get_protocol_kb
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
            
            # Null-safety check: details must exist
            if details is None:
                return self._create_guided_error_response(
                    command_type=CommandType.SWAP,
                    agent_type=AgentType.SWAP,
                    error_context=ErrorContext.MISSING_TOKEN_PAIR,
                    additional_message="Unable to parse swap command. Please provide tokens and amount."
                )
            
            # Extract swap parameters
            token_in = details.token_in.symbol if details.token_in else None
            token_out = details.token_out.symbol if details.token_out else None
            amount = details.amount
            chain_id = unified_command.chain_id
            
            # Check for missing parameters with KB-enriched suggestions
            missing_params = []
            kb_suggestions = {}
            
            if not token_in:
                missing_params.append("token_in")
            else:
                # Try KB lookup for token_in to validate it exists
                kb = get_protocol_kb()
                kb_result = kb.get(token_in)
                if kb_result:
                    kb_key, kb_entry = kb_result
                    kb_suggestions["token_in"] = {
                        "official_name": kb_entry.official_name,
                        "summary": kb_entry.summary,
                        "bridges_to": kb_entry.bridges_to,
                        "integrations_with": kb_entry.integrations_with
                    }
                    logger.info(f"KB match for {token_in}: {kb_key}")
            
            if not token_out:
                missing_params.append("token_out")
            else:
                # Try KB lookup for token_out to validate it exists
                kb = get_protocol_kb()
                kb_result = kb.get(token_out)
                if kb_result:
                    kb_key, kb_entry = kb_result
                    kb_suggestions["token_out"] = {
                        "official_name": kb_entry.official_name,
                        "summary": kb_entry.summary,
                        "bridges_to": kb_entry.bridges_to,
                        "integrations_with": kb_entry.integrations_with
                    }
                    logger.info(f"KB match for {token_out}: {kb_key}")
            
            if not amount:
                missing_params.append("amount")
            if not chain_id:
                missing_params.append("chain")
            
            if missing_params:
                # Build KB-enriched error message if we have suggestions
                additional_message = None
                if kb_suggestions and len(missing_params) == 1:
                    # If only one token is missing, suggest the other one we found
                    if "token_in" in kb_suggestions:
                        info = kb_suggestions["token_in"]
                        additional_message = f"Found '{info['official_name']}' in our knowledge base: {info['summary']}\n" \
                                           f"Available on: {', '.join(info['bridges_to'])}. Works with: {', '.join(info['integrations_with'])}"
                    elif "token_out" in kb_suggestions:
                        info = kb_suggestions["token_out"]
                        additional_message = f"Found '{info['official_name']}' in our knowledge base: {info['summary']}\n" \
                                           f"Available on: {', '.join(info['bridges_to'])}. Works with: {', '.join(info['integrations_with'])}"
                
                # Use centralized error guidance for consistent messaging
                error_context = ErrorContext.MISSING_AMOUNT if not amount else \
                               ErrorContext.MISSING_TOKEN_PAIR if not (token_in and token_out) else \
                               ErrorContext.MISSING_CHAIN
                return self._create_guided_error_response(
                    command_type=CommandType.SWAP,
                    agent_type=AgentType.SWAP,
                    error_context=error_context,
                    missing_params=missing_params,
                    additional_message=additional_message
                )
            
            # Normalize tokens for DEX compatibility
            token_in = self._normalize_token_for_swap(token_in, chain_id)
            token_out = self._normalize_token_for_swap(token_out, chain_id)
            
            # Convert USD amounts if needed
            if details.is_usd_amount:
                amount = await self._convert_usd_to_token(amount, token_in, chain_id)
            
            # Get swap quote from protocol registry
            quote = await self._get_best_swap_quote(
                token_in, token_out, amount, chain_id, unified_command.wallet_address
            )
            
            if not quote:
                return self._create_guided_error_response(
                    command_type=CommandType.SWAP,
                    agent_type=AgentType.SWAP,
                    error_context=ErrorContext.NO_LIQUIDITY,
                    additional_message=f"No swap route found for {token_in} -> {token_out} on this chain."
                )
            
            # Check if approval is needed (0x returns allowanceIssues in metadata)
            allowance_issues = quote.get("metadata", {}).get("allowanceIssues")
            if allowance_issues:
                return await self._create_approval_flow(
                    unified_command, quote, details, amount
                )
            
            # Also check explicit needs_approval flag (for other protocols)
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
        self, token_in: str, token_out: str, amount: Decimal, chain_id: int, wallet_address: str
    ) -> Optional[Dict[str, Any]]:
        """Get best swap quote from available protocols."""
        try:
            # Try protocol registry with correct method signature
            # For same-chain swaps, from_chain == to_chain
            quote = await self.protocol_registry.get_quote(
                from_token=token_in,
                to_token=token_out,
                amount=str(amount),
                from_chain=chain_id,
                to_chain=chain_id,  # Same-chain swap
                user_address=wallet_address
            )
            
            if quote and quote.get("success"):
                return quote
            
            # If registry quote failed or returned None, log and return None
            if not quote:
                logger.warning(f"Protocol registry returned no quote for {token_in} -> {token_out} on chain {chain_id}")
            else:
                logger.warning(f"Protocol registry returned unsuccessful quote: {quote.get('error', 'unknown error')}")
            
            return None
            
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
            # Extract token address from metadata (where 0x puts it)
            metadata = quote.get("metadata", {})
            token_address = metadata.get("from_token", {}).get("address")
            
            # Get allowance target from 0x metadata
            spender = metadata.get("allowanceTarget") or quote.get("spender") or quote.get("to")
            
            if not token_address or not spender:
                logger.error(f"Missing approval parameters: token_address={token_address}, spender={spender}")
                return self._create_error_response(
                    "Missing approval parameters for token approval",
                    AgentType.SWAP
                )
            
            # Convert amount to token units with proper decimals
            decimals = metadata.get("from_token", {}).get("decimals", 18)
            approval_amount = int(amount * (Decimal(10) ** decimals))
            
            # Create approval transaction using ERC20 approve
            approval_data = self._encode_approval(spender, Decimal(approval_amount))
            
            approval_tx = TransactionData(
                to=token_address,
                data=approval_data,
                value="0",
                chain_id=unified_command.chain_id,
                gas_limit="100000"
            )
            
            logger.info(f"Creating approval flow: token={token_address}, spender={spender}, amount={approval_amount}")
            
            return self._create_success_response(
                content={
                    "message": f"Approval required for {details.token_in.symbol}",
                    "type": "swap_approval",
                    "flow_info": {
                        "current_step": 1,
                        "total_steps": 2,
                        "step_type": "approval",
                        "details": {
                            "token": details.token_in.symbol,
                            "spender_contract": spender,
                            "amount": str(amount)
                        }
                    }
                },
                agent_type=AgentType.SWAP,
                transaction=approval_tx,
                awaiting_confirmation=True,
                metadata={
                    "quote": quote,
                    "next_step": "swap",
                    "approval_target": spender,
                    "token_address": token_address
                }
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
    
    def _enrich_error_with_kb_context(
        self,
        token_symbol: str,
        base_message: str
    ) -> str:
        """
        Enrich error message with knowledge base context.
        When a token fails to resolve, check KB for similar tokens and provide suggestions.
        
        Args:
            token_symbol: The token that failed to resolve
            base_message: Base error message
            
        Returns:
            Enriched error message with KB suggestions
        """
        try:
            kb = get_protocol_kb()
            kb_result = kb.get(token_symbol)
            
            if kb_result:
                kb_key, kb_entry = kb_result
                enriched = f"{base_message}\n\n" \
                          f"💡 Did you mean '{kb_entry.official_name}'? {kb_entry.summary} " \
                          f"Available on: {', '.join(kb_entry.bridges_to)}"
                logger.info(f"Enriched error with KB match: {kb_key}")
                return enriched
            else:
                # Track as miss for KB gap analysis
                logger.info(f"KB miss tracked for token: {token_symbol}")
                return base_message
                
        except Exception as e:
            logger.error(f"Failed to enrich error with KB context: {e}")
            return base_message
