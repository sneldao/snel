"""
X402 Agentic Payment Processor

Handles AI-triggered payments and automated settlement workflows using Cronos x402 protocol.
Follows the same natural integration pattern as MNEE payments.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config.chains import get_chain_info, is_x402_privacy_supported
from app.models.unified_models import (
    AgentType,
    CommandType,
    UnifiedCommand,
    UnifiedResponse,
)
from app.protocols.x402_adapter import check_x402_service_health

logger = logging.getLogger(__name__)


class X402Processor:
    """Processor for x402 agentic payment operations."""

    settings: Any

    def __init__(self, settings: Any = None, **kwargs: Any) -> None:
        self.settings = settings

    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process x402 agentic payment commands naturally."""
        try:
            command_lower = unified_command.command.lower()
            chain_id = unified_command.chain_id or 1

            # Check if user is on a supported network
            if not is_x402_privacy_supported(chain_id):
                return self._suggest_cronos_network(unified_command)

            # Determine x402 operation type based on natural language
            if (
                any(
                    keyword in command_lower
                    for keyword in [
                        "recurring",
                        "schedule",
                        "weekly",
                        "monthly",
                        "daily",
                        "hourly",
                    ]
                )
                and any(
                    pay_keyword in command_lower
                    for pay_keyword in ["payment", "pay"]
                )
                and any(
                    duration_keyword in command_lower
                    for duration_keyword in ["for", "recurring", "schedule"]
                )
            ):
                return await self._handle_recurring_payment(unified_command)
            elif any(
                keyword in command_lower
                for keyword in ["pay agent", "agent payment", "ai payment"]
            ):
                return await self._handle_ai_payment(unified_command)
            elif any(
                keyword in command_lower
                for keyword in ["settlement", "batch", "multiple payments"]
            ):
                return await self._handle_settlement(unified_command)
            elif "pay" in command_lower and (
                "to" in command_lower or "@" in command_lower or ".eth" in command_lower
            ):
                # Simple one-time payment - handle as direct X402 payment
                return await self._handle_simple_payment(unified_command)
            else:
                # Check for automation keywords first
                return await self._handle_ai_payment(unified_command)

        except Exception as e:
            logger.error(f"X402 processing error: {e}")
            return UnifiedResponse(
                content=f"I encountered an issue with the x402 payment: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT},
            )

    def _suggest_cronos_network(
        self, unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Suggest switching to Cronos for x402 functionality."""
        chain_id = unified_command.chain_id or 1
        chain_info = get_chain_info(chain_id)
        current_chain = chain_info.name if chain_info else f"Chain {chain_id}"

        metadata: dict[str, Any] = {
            "suggested_chains": [25, 338],
            "current_chain": chain_id,
            "command_type": CommandType.X402_PAYMENT,
        }

        message = (
            f"X402 agentic payments are available on **Cronos EVM**! 🤖\n\n"
            f"You're currently on {current_chain}. To use AI-triggered payments and automated settlements, "
            f"please switch to:\n"
            f"• **Cronos Mainnet** (Chain ID: 25) for production\n"
            f"• **Cronos Testnet** (Chain ID: 338) for testing\n\n"
            f"Once connected, you can use commands like:\n"
            f"• `pay agent 10 USDC for API calls`\n"
            f"• `setup weekly payment of 100 USDC to supplier.eth`\n"
            f"• `process batch settlement for contractors`"
        )

        return UnifiedResponse(
            content={"message": message, "metadata": metadata},
            agent_type=AgentType.DEFAULT,
            status="success",
            metadata=metadata,
        )

    async def _handle_ai_payment(
        self, unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle AI-triggered payments with real x402 execution."""
        try:
            # Use parsed details from unified command if available
            if (
                unified_command.details
                and unified_command.details.amount
                and unified_command.details.token_in
            ):
                payment_details = {
                    "amount": str(unified_command.details.amount),
                    "asset": unified_command.details.token_in.symbol,
                    "recipient": await self._extract_recipient_from_command(
                        unified_command.command
                    ),
                }
            else:
                # Fallback to natural language parsing
                payment_details = await self._parse_payment_command(
                    unified_command.command
                )

            if not payment_details:
                message = (
                    "I can help you set up automated DeFi services! 🤖\n\n"
                    "**Popular automations:**\n"
                    "• `setup monthly portfolio rebalancing with 50 USDC budget`\n"
                    "• `pay 20 USDC to rebalance when my ETH allocation drops below 30%`\n"
                    "• `setup weekly 100 USDC for yield farming when APY > 15%`\n\n"
                    "**Recurring payments:**\n"
                    "• `setup monthly payment of 100 USDC to supplier.eth`\n"
                    "• `setup weekly 25 MNEE payment to globalnative.eth`\n\n"
                    "These use **Cronos x402** to execute automatically when conditions are met."
                )
                return UnifiedResponse(
                    content={
                        "message": message,
                        "metadata": {"command_type": CommandType.X402_PAYMENT},
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success",
                    awaiting_confirmation=True,
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Detect automation type
            automation_type = self._detect_automation_type(unified_command.command)

            # Determine network and supported stablecoin
            chain_id = unified_command.chain_id or 1
            if chain_id == 338:
                network = "cronos-testnet"
                supported_token = "USDC"
            elif chain_id == 25:
                network = "cronos-mainnet"
                supported_token = "USDC"
            elif chain_id == 1:
                network = "ethereum-mainnet"
                supported_token = "MNEE"
            else:
                network = "cronos-testnet"
                supported_token = "USDC"

            # Validate amount and token
            if payment_details["asset"].upper() not in ["USDC", "MNEE"]:
                return UnifiedResponse(
                    content=f"❌ **Token Not Supported**\n\n"
                    f"X402 supports **USDC** on Cronos and **MNEE** on Ethereum.\n"
                    f"You specified: {payment_details['asset']}\n\n"
                    f"Please try: `setup portfolio rebalancing with {payment_details['amount']} {supported_token} budget`",
                    agent_type=AgentType.ERROR,
                    status="error",
                    error=f"Unsupported token: {payment_details['asset']}",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Validate token matches network
            asset_upper = payment_details["asset"].upper()
            if (asset_upper == "USDC" and chain_id == 1) or (
                asset_upper == "MNEE" and chain_id in [25, 338]
            ):
                chain_info = get_chain_info(chain_id)
                chain_name = chain_info.name if chain_info else f"Chain {chain_id}"
                return UnifiedResponse(
                    content=f"❌ **Token/Network Mismatch**\n\n"
                    f"On {chain_name}, please use **{supported_token}**.\n"
                    f"You specified: {payment_details['asset']}\n\n"
                    f"Please try: `setup portfolio rebalancing with {payment_details['amount']} {supported_token} budget`",
                    agent_type=AgentType.ERROR,
                    status="error",
                    error=f"Token {asset_upper} not supported on this network",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Check facilitator health
            is_healthy = await check_x402_service_health(network)

            if not is_healthy:
                return UnifiedResponse(
                    content=f"❌ **X402 Service Unavailable**\n\n"
                    f"The Cronos x402 facilitator service is currently unavailable.\n"
                    f"Please try again later or check the service status.",
                    agent_type=AgentType.ERROR,
                    status="error",
                    error="X402 facilitator service unavailable",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Create automation-specific response
            return await self._create_automation_response(
                automation_type, payment_details, unified_command, network, is_healthy
            )

        except Exception as e:
            logger.error(f"AI payment error: {e}")
            return UnifiedResponse(
                content=f"I encountered an issue with the x402 payment: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT},
            )

    def _detect_automation_type(self, command: str) -> str:
        """Detect the type of automation from the command."""
        command_lower = command.lower()

        if any(
            word in command_lower for word in ["rebalancing", "rebalance", "portfolio"]
        ):
            return "portfolio_rebalancing"
        elif any(word in command_lower for word in ["yield", "farming", "apy"]):
            return "yield_farming"
        elif any(word in command_lower for word in ["bridge", "cross-chain"]):
            return "cross_chain_automation"
        elif any(
            word in command_lower
            for word in ["buy", "sell", "trade", "when", "drops", "below", "above"]
        ):
            return "conditional_trading"
        elif (
            any(
                word in command_lower
                for word in ["recurring", "weekly", "monthly", "daily"]
            )
            and "payment" in command_lower
        ):
            return "recurring_payment"
        else:
            return "general_automation"

    async def _create_automation_response(
        self,
        automation_type: str,
        payment_details: dict[str, Any],
        unified_command: UnifiedCommand,
        network: str,
        is_healthy: bool,
    ) -> UnifiedResponse:
        """Create automation-specific response."""

        # Override network for MNEE
        if payment_details.get("asset", "").upper() == "MNEE":
            network = "ethereum-mainnet"

        if automation_type == "portfolio_rebalancing":
            metadata = {
                "automation_type": "portfolio_rebalancing",
                "budget": float(payment_details["amount"]),
                "asset": payment_details["asset"],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Automated portfolio rebalancing when allocation drifts >5%",
                "command_type": CommandType.X402_PAYMENT,
            }
            return UnifiedResponse(
                content={
                    "message": f"🎯 **Automated Portfolio Rebalancing Setup**\n\n"
                    f"**Service Details:**\n"
                    f"• Monthly Budget: {payment_details['amount']} {payment_details['asset']}\n"
                    f"• Trigger: When allocation drifts >5% from target\n"
                    f"• Network: Cronos {'Testnet' if unified_command.chain_id == 338 else 'Mainnet'} (low fees)\n"
                    f"• Execution: Automatic via x402 when needed\n\n"
                    f"**How it works:**\n"
                    f"1. I monitor your portfolio allocation 24/7\n"
                    f"2. When rebalancing is needed, x402 authorizes payment\n"
                    f"3. Trades execute automatically to restore target allocation\n"
                    f"4. You stay balanced without manual intervention\n\n"
                    f"**Ready to authorize?** This will enable autonomous portfolio management.",
                    "type": "x402_automation",
                    "metadata": metadata,
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

        elif automation_type == "yield_farming":
            metadata = {
                "automation_type": "yield_farming",
                "budget": float(payment_details["amount"]),
                "asset": payment_details["asset"],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Automated yield farming when APY > 15%",
                "command_type": CommandType.X402_PAYMENT,
            }
            message = (
                f"🌾 **Automated Yield Farming Setup**\n\n"
                f"**Service Details:**\n"
                f"• Monthly Budget: {payment_details['amount']} {payment_details['asset']}\n"
                f"• Trigger: When targeted protocol APY > 15%\n"
                f"• Network: Cronos {'Testnet' if unified_command.chain_id == 338 else 'Mainnet'}\n"
                f"• Execution: Automatic via x402 for compounding and allocation\n\n"
                f"**How it works:**\n"
                f"1. I track yields across supported protocols\n"
                f"2. When conditions are optimal, x402 authorizes the deposit\n"
                f"3. Your funds are moved into the highest yielding pool automatically\n"
                f"4. We harvest and compound on your behalf\n\n"
                f"**Ready to farm autonomously?** Please authorize the setup."
            )
            return UnifiedResponse(
                content={
                    "message": message,
                    "type": "x402_automation",
                    "metadata": metadata,
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

        elif automation_type == "cross_chain_automation":
            metadata = {
                "automation_type": "cross_chain_automation",
                "budget": float(payment_details["amount"]),
                "asset": payment_details["asset"],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Automated cross-chain bridging on schedule",
                "command_type": CommandType.X402_PAYMENT,
            }
            return UnifiedResponse(
                content={
                    "message": f"🌉 **Automated Cross-Chain Bridge Setup**\n\n"
                    f"**Service Details:**\n"
                    f"• Budget: {payment_details['amount']} {payment_details['asset']}\n"
                    f"• Trigger: Monthly automated bridging\n"
                    f"• Network: Cronos {'Testnet' if unified_command.chain_id == 338 else 'Mainnet'}\n"
                    f"• Execution: Automatic via x402 when scheduled\n\n"
                    f"**How it works:**\n"
                    f"1. I monitor your bridge schedule 24/7\n"
                    f"2. When it's time to bridge, x402 authorizes transfer\n"
                    f"3. Funds bridge automatically to destination chain\n"
                    f"4. You maintain liquidity across chains effortlessly\n\n"
                    f"**Ready to bridge?** This enables autonomous cross-chain management.",
                    "type": "x402_automation",
                    "metadata": metadata,
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

        elif automation_type == "recurring_payment":
            # Redirect to recurring payment handler
            return await self._handle_recurring_payment(unified_command)

        elif automation_type == "conditional_trading":
            metadata = {
                "automation_type": "conditional_trading",
                "budget": float(payment_details["amount"]),
                "asset": payment_details["asset"],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Conditional trade execution based on market triggers",
                "command_type": CommandType.X402_PAYMENT,
            }
            return UnifiedResponse(
                content={
                    "message": f"📈 **Conditional Trading Setup**\n\n"
                    f"**Trade Details:**\n"
                    f"• Budget: {payment_details['amount']} {payment_details['asset']}\n"
                    f"• Condition: Based on your specified trigger\n"
                    f"• Network: Cronos {'Testnet' if unified_command.chain_id == 338 else 'Mainnet'}\n"
                    f"• Execution: Automatic via x402 when condition met\n\n"
                    f"**How it works:**\n"
                    f"1. I monitor market conditions 24/7\n"
                    f"2. When your condition is met, x402 authorizes trade\n"
                    f"3. Trade executes automatically at optimal timing\n"
                    f"4. You never miss opportunities while offline\n\n"
                    f"**Ready to set the trap?** This enables autonomous market execution.",
                    "type": "x402_automation",
                    "metadata": metadata,
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

        else:
            # General automation
            metadata = {
                "automation_type": "general_automation",
                "budget": float(payment_details["amount"]),
                "asset": payment_details["asset"],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "General DeFi automation services",
                "command_type": CommandType.X402_PAYMENT,
            }
            message = (
                f"🤖 **DeFi Automation Service**\n\n"
                f"**Service Details:**\n"
                f"• Monthly Allowance: {payment_details['amount']} {payment_details['asset']}\n"
                f"• Trigger: Automated agent execution\n"
                f"• Network: {network.replace('-', ' ').title()}\n"
                f"• Execution: Secure x402 authorization\n\n"
                f"**How it works:**\n"
                f"1. You authorize me to perform specific automated tasks\n"
                f"2. When a task needs to execute, x402 handles the payment settlement\n"
                f"3. You receive a report of all autonomous actions taken\n"
                f"4. You maintain full control and can revoke access anytime\n\n"
                f"**Would you like to authorize this automation agent?**"
            )
            return UnifiedResponse(
                content={
                    "message": message,
                    "type": "x402_automation",
                    "metadata": metadata,
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

    async def _handle_recurring_payment(
        self, unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle recurring payment setup with natural conversation."""
        from app.domains.payment_actions.models import PaymentActionFrequency

        try:
            payment_details = await self._parse_recurring_command(
                unified_command.command
            )

            if not payment_details:
                message = (
                    "Let me help you set up a recurring payment! 🔄\n\n"
                    "**You can say things like:**\n"
                    "• `setup monthly payment of 100 USDC to supplier.eth`\n"
                    "• `pay 25 MNEE weekly to globalnative.eth`\n"
                    "• `schedule daily 1 USDC for automated testing`"
                )
                return UnifiedResponse(
                    content={
                        "message": message,
                        "metadata": {"command_type": CommandType.X402_PAYMENT},
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success",
                    awaiting_confirmation=True,
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Determine network based on asset
            if payment_details["asset"].upper() == "MNEE":
                network = "ethereum-mainnet"
            else:
                # Default to Cronos for USDC and others
                network = (
                    "cronos-testnet"
                    if unified_command.chain_id == 338
                    else "cronos-mainnet"
                )

            # Map frequency and calculate approval cap based on custom duration
            freq_map = {
                "hourly": (PaymentActionFrequency.HOURLY, 24 * 365),  # Hours in a year
                "daily": (PaymentActionFrequency.DAILY, 365),
                "weekly": (PaymentActionFrequency.WEEKLY, 52),
                "monthly": (PaymentActionFrequency.MONTHLY, 12),
            }

            freq_enum, default_periods = freq_map.get(
                payment_details["interval"].lower(),
                (PaymentActionFrequency.MONTHLY, 12),
            )
            frequency = freq_enum

            single_amount = float(payment_details["amount"])

            # Handle limited duration payments
            if payment_details.get("limited_duration"):
                duration_count = int(payment_details["duration_count"])
                duration_unit = payment_details["duration_unit"]
                
                # Calculate total payments based on duration
                if duration_unit == "hours" and frequency == PaymentActionFrequency.HOURLY:
                    total_payments = duration_count
                elif duration_unit == "days" and frequency == PaymentActionFrequency.DAILY:
                    total_payments = duration_count
                elif duration_unit == "weeks" and frequency == PaymentActionFrequency.WEEKLY:
                    total_payments = duration_count
                elif duration_unit == "months" and frequency == PaymentActionFrequency.MONTHLY:
                    total_payments = duration_count
                else:
                    # Default fallback
                    total_payments = default_periods
                
                approval_amount = single_amount * total_payments
                budget_months = max(1, duration_count // (12 if duration_unit == "months" else 1))
            else:
                # Respect custom budget cap duration from frontend
                budget_months = int(payment_details.get("budget_cap_months", 12))

                # Calculate approval amount based on actual duration
                if frequency == PaymentActionFrequency.HOURLY:
                    approval_amount = single_amount * (24 * 365 * budget_months / 12)
                elif frequency == PaymentActionFrequency.DAILY:
                    approval_amount = single_amount * (365 * budget_months / 12)
                elif frequency == PaymentActionFrequency.WEEKLY:
                    approval_amount = single_amount * (52 * budget_months / 12)
                else:  # Monthly
                    approval_amount = single_amount * budget_months

            # action_id is not available yet, will be created on confirmation
            action_id = None

            metadata = {
                "payment_type": "recurring",
                "interval": payment_details["interval"],
                "amount": payment_details["amount"],
                "asset": payment_details["asset"],
                "recipient": payment_details["recipient"],
                "network": network,
                "requires_signature": True,
                "command_type": CommandType.X402_PAYMENT,
                "automation_type": "recurring_payment",
                "action_id": action_id,
                "approval_amount": str(approval_amount),
                "budget_cap_months": budget_months,  # Include custom duration
            }

            # Format network name for display
            if network == "ethereum-mainnet":
                network_display = "Ethereum Mainnet"
            else:
                network_display = (
                    f"Cronos {'Testnet' if 'testnet' in network else 'Mainnet'}"
                )

            # Format duration display
            if payment_details.get("limited_duration"):
                duration_count = payment_details["duration_count"]
                duration_unit = payment_details["duration_unit"]
                duration_text = f"{duration_count} {duration_unit}"
                budget_cap_text = f"{approval_amount} {payment_details['asset']} total"
            else:
                duration_text = (
                    f"{budget_months}-month" if budget_months != 12 else "1-year"
                )
                budget_cap_text = f"{duration_text} budget cap ({approval_amount} {payment_details['asset']})"

            return UnifiedResponse(
                content={
                    "message": f"🔄 **Recurring Payment Setup**\n\n"
                    f"**Payment Schedule:**\n"
                    f"• Frequency: {payment_details['interval'].title()}\n"
                    f"• Amount: {payment_details['amount']} {payment_details['asset']}\n"
                    f"• Recipient: {payment_details['recipient']}\n"
                    f"• Duration: {duration_text}\n"
                    f"• Network: {network_display}\n\n"
                    f"This will create a **Payment Action** that uses {network_display.split()[0]} X402 for secure settlement.\n\n"
                    f"🔒 **Security Note**: You will approve a **{budget_cap_text}** "
                    f"rather than unlimited access, ensuring you stay in control.\n\n"
                    f"*The recurring payment will be active once you authorize the Payment Action.*",
                    "type": "x402_automation",
                    "metadata": metadata,
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Recurring payment error: {e}")
            return UnifiedResponse(
                content=f"I had trouble setting up that recurring payment: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT},
            )

    async def _handle_settlement(
        self, unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle batch settlement operations."""
        try:
            metadata = {
                "payment_type": "batch_settlement",
                "network": "cronos-testnet"
                if unified_command.chain_id == 338
                else "cronos-mainnet",
                "command_type": CommandType.X402_PAYMENT,
            }
            message = (
                f"📦 **Batch Settlement Processing**\n\n"
                f"I can help you process multiple payments efficiently using **Cronos x402 batching**.\n\n"
                f"**Settlement Options:**\n"
                f"• Process payments to multiple contractors\n"
                f"• Settle cross-chain automated trades\n"
                f"• Bulk distribute rewards or allocations\n\n"
                f"*Would you like me to help you set up a specific batch payment?*"
            )
            return UnifiedResponse(
                content={"message": message, "metadata": metadata},
                agent_type=AgentType.DEFAULT,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Settlement error: {e}")
            return UnifiedResponse(
                content=f"I encountered an error with the settlement process: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT},
            )

    async def _handle_general_x402_info(
        self, unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Provide information about x402 capabilities."""
        metadata = {
            "info_type": "x402_capabilities",
            "network": "cronos-testnet"
            if unified_command.chain_id == 338
            else "cronos-mainnet",
            "command_type": CommandType.X402_PAYMENT,
        }
        message = (
            "🤖 **X402 Agentic Payment System**\n\n"
            "The **Cronos x402** protocol allows SNEL to perform autonomous DeFi operations "
            "on your behalf while you maintain full control of your funds.\n\n"
            "**Key capabilities:**\n"
            "• **Agentic Payments**: Allow AI to trigger payments for specific services\n"
            "• **Automated Yield Farming**: Securely auto-compound and rebalance yields\n"
            "• **Compliance-Ready Privacy**: Fast, private transactions with selective disclosure\n"
            "• **Recurring Settlements**: Set up weekly or monthly subscriptions effortlessly\n\n"
            "It uses a facilitator-based model that separates intent authorization from execution, "
            "with EIP-712 authorization and automated settlement workflows."
        )
        return UnifiedResponse(
            content={"message": message, "metadata": metadata},
            agent_type=AgentType.DEFAULT,
            status="success",
            metadata=metadata,
        )

    async def _parse_payment_command(self, command: str) -> dict[str, str] | None:
        """Parse payment details from natural language command."""
        import re

        # Extract amount and asset - more flexible pattern
        amount_match = re.search(r"(\d+(?:\.\d+)?)\s*([A-Z]{2,5})", command.upper())
        if not amount_match:
            return None

        amount = amount_match.group(1)
        asset = amount_match.group(2)

        recipient = await self._extract_recipient_from_command(command)
        if not recipient:
            return None

        return {"amount": amount, "asset": asset, "recipient": recipient}

    async def _extract_recipient_from_command(self, command: str) -> str | None:
        """Extract recipient from command with real address resolution."""
        import re

        # Extract recipient with proper address resolution
        recipient_patterns = [
            r"to\s+(0x[a-fA-F0-9]{40})",  # Direct Ethereum address
            r"pay\s+(0x[a-fA-F0-9]{40})",  # Direct Ethereum address
            r"to\s+([a-zA-Z0-9._-]+\.eth)",  # ENS name
            r"pay\s+([a-zA-Z0-9._-]+\.eth)",  # ENS name
        ]

        for pattern in recipient_patterns:
            match = re.search(pattern, command.lower())
            if match:
                captured = match.group(1)
                recipient = await self._resolve_recipient_address(captured)
                if recipient:
                    return recipient

        return None

    async def _parse_recurring_command(self, command: str) -> dict[str, str] | None:
        """Parse recurring payment details from natural language command."""
        import re

        # Extract amount and asset - more flexible pattern
        amount_match = re.search(r"(\d+(?:\.\d+)?)\s*([A-Z]{2,5})", command.upper())
        if not amount_match:
            return None

        amount = amount_match.group(1)
        asset = amount_match.group(2)

        # Extract interval with duration support
        interval = "monthly"  # Default
        duration_count = None
        duration_unit = None
        
        # Check for hourly patterns
        hourly_match = re.search(r"hourly\s+for\s+(\w+)\s+(hours?)", command.lower())
        if hourly_match:
            interval = "hourly"
            duration_text = hourly_match.group(1)
            duration_unit = "hours"
            
            # Convert text numbers to integers
            text_to_num = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
            }
            duration_count = text_to_num.get(duration_text, int(duration_text) if duration_text.isdigit() else None)
        
        # Check for other intervals
        elif "daily" in command.lower():
            interval = "daily"
            daily_match = re.search(r"daily\s+for\s+(\d+)\s+(days?)", command.lower())
            if daily_match:
                duration_count = int(daily_match.group(1))
                duration_unit = "days"
        elif "weekly" in command.lower():
            interval = "weekly"
            weekly_match = re.search(r"weekly\s+for\s+(\d+)\s+(weeks?)", command.lower())
            if weekly_match:
                duration_count = int(weekly_match.group(1))
                duration_unit = "weeks"
        elif "monthly" in command.lower():
            interval = "monthly"
            monthly_match = re.search(r"monthly\s+for\s+(\d+)\s+(months?)", command.lower())
            if monthly_match:
                duration_count = int(monthly_match.group(1))
                duration_unit = "months"

        recipient = await self._extract_recipient_from_command(command)
        if not recipient:
            return None

        result = {
            "amount": amount,
            "asset": asset,
            "recipient": recipient,
            "interval": interval,
        }
        
        # Add duration info if present
        if duration_count and duration_unit:
            result["duration_count"] = str(duration_count)
            result["duration_unit"] = duration_unit
            result["limited_duration"] = True
        
        return result

    async def _resolve_recipient_address(self, recipient_input: str) -> str | None:
        """
        Resolve recipient input to a valid Ethereum address.

        Args:
            recipient_input: Can be an Ethereum address, ENS name, or keyword

        Returns:
            Valid Ethereum address or None if resolution fails
        """
        from web3 import Web3

        # If it's already a valid Ethereum address, return as-is
        if recipient_input.startswith("0x") and len(recipient_input) == 42:
            return recipient_input

        # Use centralized TokenQueryService for ENS resolution
        from app.services.token_query_service import token_query_service

        resolved_address, _ = await token_query_service.resolve_address_async(
            recipient_input
        )
        if resolved_address:
            return Web3.to_checksum_address(resolved_address)

        return None

    async def _handle_simple_payment(
        self, unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle simple one-time X402 payments."""
        try:
            # Parse payment details from the command
            if (
                unified_command.details
                and unified_command.details.amount
                and unified_command.details.token_in
            ):
                amount = float(unified_command.details.amount)
                token = unified_command.details.token_in.symbol.upper()
                recipient = await self._extract_recipient_from_command(
                    unified_command.command
                )
            else:
                # Fallback parsing
                payment_details = await self._parse_payment_command(
                    unified_command.command
                )
                if not payment_details:
                    return UnifiedResponse(
                        content="I couldn't parse the payment details. Please try: `pay 1 USDC to 0x... on cronos`",
                        agent_type=AgentType.ERROR,
                        status="error",
                        metadata={"command_type": CommandType.X402_PAYMENT},
                    )

                amount = float(payment_details["amount"])
                token = payment_details["asset"].upper()
                recipient = payment_details["recipient"]

            # Validate recipient
            if not recipient:
                return UnifiedResponse(
                    content="I need a recipient address. Please try: `pay 1 USDC to 0x... on cronos`",
                    agent_type=AgentType.ERROR,
                    status="error",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Resolve recipient address
            resolved_recipient = await self._resolve_recipient_address(recipient)
            if not resolved_recipient:
                return UnifiedResponse(
                    content=f"I couldn't resolve the recipient address: {recipient}",
                    agent_type=AgentType.ERROR,
                    status="error",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Determine network
            chain_id = unified_command.chain_id or 25
            if chain_id == 25:
                network = "cronos-mainnet"
            elif chain_id == 338:
                network = "cronos-testnet"
            elif chain_id == 1:
                network = "ethereum-mainnet"
            else:
                network = "cronos-mainnet"  # Default to Cronos mainnet

            # Validate token for network
            if network.startswith("cronos") and token not in ["USDC"]:
                return UnifiedResponse(
                    content=f"❌ **Token Not Supported on Cronos**\n\nCronos X402 supports **USDC** only.\nYou specified: {token}",
                    agent_type=AgentType.ERROR,
                    status="error",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )
            elif network == "ethereum-mainnet" and token not in ["MNEE"]:
                return UnifiedResponse(
                    content=f"❌ **Token Not Supported on Ethereum**\n\nEthereum X402 supports **MNEE** only.\nYou specified: {token}",
                    agent_type=AgentType.ERROR,
                    status="error",
                    metadata={"command_type": CommandType.X402_PAYMENT},
                )

            # Create payment confirmation response
            return UnifiedResponse(
                content={
                    "message": f"💳 **X402 Payment Ready**\n\n"
                    f"**Payment Details:**\n"
                    f"• Amount: {amount} {token}\n"
                    f"• Recipient: {resolved_recipient}\n"
                    f"• Network: {network.replace('-', ' ').title()}\n\n"
                    f"This will be executed as a secure X402 payment with EIP-712 signing.",
                    "type": "x402_payment",
                    "payment_details": {
                        "amount": amount,
                        "token": token,
                        "recipient": resolved_recipient,
                        "network": network,
                    },
                    "requires_transaction": True,
                },
                agent_type=AgentType.PAYMENT,
                status="success",
                awaiting_confirmation=True,
                metadata={
                    "command_type": CommandType.X402_PAYMENT,
                    "payment_type": "simple",
                    "network": network,
                    "amount": amount,
                    "token": token,
                    "recipient": resolved_recipient,
                },
            )

        except Exception as e:
            logger.error(f"Simple payment error: {e}")
            return UnifiedResponse(
                content=f"I had trouble processing that payment: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT},
            )
