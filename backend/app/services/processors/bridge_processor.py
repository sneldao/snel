"""
Bridge command processor.
Handles cross-chain bridging operations.
"""
import logging
from typing import Dict, Any, Optional

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, TransactionData, CommandType
)
from app.core.exceptions import BusinessLogicError
from app.services.error_guidance_service import ErrorContext
from app.services.knowledge_base import get_protocol_kb
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
            
            # Null-safety check: details must exist
            if details is None:
                return self._create_guided_error_response(
                    command_type=CommandType.BRIDGE,
                    agent_type=AgentType.BRIDGE,
                    error_context=ErrorContext.MISSING_TOKEN,
                    additional_message="Unable to parse bridge command. Please provide token, amount, and destination chain."
                )
            
            # Extract bridge parameters
            token = details.token_in.symbol if details.token_in else None
            amount = details.amount
            from_chain = unified_command.chain_id
            to_chain = details.destination_chain
            
            # Check for missing parameters with KB-enriched suggestions
            missing_params = []
            kb_suggestions = {}
            
            if not token:
                missing_params.append("token")
            else:
                # Try KB lookup for token to validate it exists
                kb = get_protocol_kb()
                kb_result = kb.get(token)
                if kb_result:
                    kb_key, kb_entry = kb_result
                    kb_suggestions["token"] = {
                        "official_name": kb_entry.official_name,
                        "summary": kb_entry.summary,
                        "bridges_to": kb_entry.bridges_to
                    }
                    logger.info(f"KB match for {token}: {kb_key}")
            
            if not amount:
                missing_params.append("amount")
            if not from_chain:
                missing_params.append("source chain")
            if not to_chain:
                missing_params.append("destination chain")
            
            if missing_params:
                # Build KB-enriched error message if we have suggestions
                additional_message = None
                if kb_suggestions and "token" in kb_suggestions:
                    info = kb_suggestions["token"]
                    additional_message = f"Found '{info['official_name']}' in our knowledge base: {info['summary']}\n" \
                                       f"Can bridge to: {', '.join(info['bridges_to'])}"
                
                # Use centralized error guidance for consistent messaging
                error_context = ErrorContext.MISSING_AMOUNT if not amount else \
                               ErrorContext.MISSING_TOKEN if not token else \
                               ErrorContext.MISSING_DESTINATION if not to_chain else \
                               ErrorContext.MISSING_CHAIN
                return self._create_guided_error_response(
                    command_type=CommandType.BRIDGE,
                    agent_type=AgentType.BRIDGE,
                    error_context=error_context,
                    missing_params=missing_params,
                    additional_message=additional_message
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
        """Process bridge using GMP (Axelar)."""
        # Brian API has been removed. Bridge feature delegates to GMP/Axelar
        # which is handled in the main bridge processing flow
        return await self.process_bridge(
            unified_command, token, amount, from_chain, to_chain
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
            
            # Check for missing parameters
            missing_params = []
            if not token:
                missing_params.append("token")
            if not amount:
                missing_params.append("amount")
            if not from_chain:
                missing_params.append("chain")
            
            if missing_params:
                # Use centralized error guidance for consistent messaging
                error_context = ErrorContext.MISSING_AMOUNT if not amount else \
                               ErrorContext.MISSING_TOKEN if not token else \
                               ErrorContext.MISSING_CHAIN
                return self._create_guided_error_response(
                    command_type=CommandType.BRIDGE_TO_PRIVACY,
                    agent_type=AgentType.BRIDGE_TO_PRIVACY,
                    error_context=error_context,
                    missing_params=missing_params
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
            
            # Generate unique bridge ID for status tracking
            import uuid
            bridge_id = str(uuid.uuid4())

            transaction = TransactionData(
                to=first_step.get("to"),
                data=first_step.get("data"),
                value=first_step.get("value", "0"),
                chain_id=from_chain,
                gas_limit=first_step.get("gas_limit", "500000")
            )
            
            # Build comprehensive response with wallet guidance
            return self._create_success_response(
                content={
                    "message": f"Ready to bridge {amount} {token} to Zcash privacy pool\n\n"
                              f"Your transaction details (addresses, amounts) will be hidden on the Zcash blockchain.\n\n"
                              f"After bridging, you'll need a shielded-by-default wallet like:\n"
                              f"• Zashi (mobile)\n"
                              f"• Nighthawk (desktop)\n\n"
                              f"We'll help you receive your private funds.",
                    "type": "bridge_privacy_ready",
                    "bridge_id": bridge_id,
                    "amount": str(amount),
                    "token": token,
                    "from_chain": self._get_chain_name(from_chain),
                    "to_chain": "Zcash",
                    "protocol": "Axelar GMP",
                    "estimated_time": gmp_result.get("estimated_time", "5-10 minutes"),
                    "privacy_level": "High (Shielded)",
                    "requires_transaction": True,
                    "steps": steps,
                    "post_bridge_guidance": {
                        "title": "After Bridging",
                        "instructions": [
                            {
                                "step": 1,
                                "title": "Confirm Transaction",
                                "description": "Sign the bridge transaction in your connected wallet"
                            },
                            {
                                "step": 2,
                                "title": "Wait for Confirmation",
                                "description": f"Bridge completes in approximately {gmp_result.get('estimated_time', '5-10 minutes')}"
                            },
                            {
                                "step": 3,
                                "title": "Get a Zcash Wallet",
                                "description": "Download Zashi (mobile) or Nighthawk (desktop) - both are shielded by default"
                            },
                            {
                                "step": 4,
                                "title": "Receive Your Private Funds",
                                "description": "Your bridged assets will appear automatically in your shielded address"
                            }
                        ],
                        "recommended_wallets": [
                            {
                                "name": "Zashi",
                                "type": "Mobile",
                                "url": "https://zashi.app/",
                                "reason": "Official Zcash mobile wallet, shielded by default"
                            },
                            {
                                "name": "Nighthawk",
                                "type": "Desktop",
                                "url": "https://nighthawkwallet.com/",
                                "reason": "Full desktop support, shielded by default"
                            }
                        ],
                        "security_tips": [
                            "Always use a wallet marked 'shielded by default'",
                            "Save your recovery phrase securely",
                            "Only enter your address in trusted applications",
                            "Verify wallet URLs before downloading"
                        ]
                    }
                },
                agent_type=AgentType.BRIDGE_TO_PRIVACY,
                transaction=transaction,
                awaiting_confirmation=True,
                metadata={
                    "gmp_result": gmp_result,
                    "privacy_enabled": True,
                    "axelar_powered": True,
                    "wallet_guidance_provided": True
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
    
    def create_post_bridge_success_response(
        self,
        bridge_id: str,
        amount: str,
        token: str,
        from_chain: str,
        wallet_address: str,
        estimated_arrival_time: str = "5-10 minutes"
    ) -> UnifiedResponse:
        """
        Create post-bridge success response for display after bridge completes.
        
        Shows receiving address, action cards (Receive/Spend/Learn), and next steps.
        """
        return self._create_success_response(
            content={
                "message": f"Bridge complete! Your {amount} {token} is arriving in {estimated_arrival_time}",
                "type": "post_bridge_success",
                "bridge_id": bridge_id,
                "amount": amount,
                "token": token,
                "from_chain": from_chain,
                "to_chain": "Zcash",
                "receiving_address": wallet_address,
                "estimated_arrival_time": estimated_arrival_time,
                "actions": [
                    {
                        "id": "receive",
                        "title": "Receive Funds",
                        "description": "Copy your address and import into your wallet",
                        "icon": "wallet",
                        "cta_text": "Get Address",
                    },
                    {
                        "id": "spend",
                        "title": "Spend Privately",
                        "description": "Browse merchants accepting Zcash payments",
                        "icon": "shopping",
                        "cta_text": "View Merchants",
                        "cta_url": "https://paywithz.cash/",
                    },
                    {
                        "id": "learn",
                        "title": "Learn More",
                        "description": "Understand privacy and best practices",
                        "icon": "book",
                        "cta_text": "Read Guide",
                        "cta_url": "https://z.cash/learn/",
                    },
                ],
                "next_steps": [
                    "Copy your receiving address (shown above)",
                    "Open your Zcash wallet (Zashi or Nighthawk)",
                    "Import the address or wait for automatic arrival",
                    "Your funds will appear in your shielded balance",
                ]
            },
            agent_type=AgentType.BRIDGE_TO_PRIVACY,
            metadata={
                "bridge_id": bridge_id,
                "post_bridge_state": True,
                "privacy_enabled": True,
            }
        )
