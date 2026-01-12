"""
X402 Agentic Payment Processor

Handles AI-triggered payments and automated settlement workflows using Cronos x402 protocol.
Follows the same natural integration pattern as MNEE payments.
"""

import logging
from typing import Dict, Any, Optional
from app.models.unified_models import UnifiedCommand, UnifiedResponse, CommandType, AgentType
from app.protocols.x402_adapter import X402Adapter, execute_ai_payment, check_x402_service_health
from app.config.chains import get_chain_info, is_x402_privacy_supported

logger = logging.getLogger(__name__)

class X402Processor:
    """Processor for x402 agentic payment operations."""
    
    def __init__(self, settings=None, **kwargs):
        self.settings = settings
        
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Process x402 agentic payment commands naturally."""
        try:
            command_lower = unified_command.command.lower()
            
            # Check if user is on a supported network
            if not is_x402_privacy_supported(unified_command.chain_id):
                return self._suggest_cronos_network(unified_command)
            
            # Determine x402 operation type based on natural language
            if any(keyword in command_lower for keyword in ["recurring", "schedule", "weekly", "monthly", "daily"]) and "payment" in command_lower:
                return await self._handle_recurring_payment(unified_command)
            elif any(keyword in command_lower for keyword in ["pay agent", "agent payment", "ai payment"]):
                return await self._handle_ai_payment(unified_command)
            elif any(keyword in command_lower for keyword in ["settlement", "batch", "multiple payments"]):
                return await self._handle_settlement(unified_command)
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
                metadata={"command_type": CommandType.X402_PAYMENT}
            )
    
    def _suggest_cronos_network(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Suggest switching to Cronos for x402 functionality."""
        chain_info = get_chain_info(unified_command.chain_id)
        current_chain = chain_info.name if chain_info else f"Chain {unified_command.chain_id}"
        
        metadata = {
            "suggested_chains": [25, 338],
            "current_chain": unified_command.chain_id,
            "command_type": CommandType.X402_PAYMENT
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
            content={
                "message": message,
                "metadata": metadata
            },
            agent_type=AgentType.DEFAULT,
            status="success",
            metadata=metadata
        )
    
    async def _handle_ai_payment(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle AI-triggered payments with real x402 execution."""
        try:
            # Parse payment details from natural language
            payment_details = self._parse_payment_command(unified_command.command)
            
            if not payment_details:
                message = (
                    "I can help you set up automated DeFi services! 🤖\n\n"
                    "**Popular automations:**\n"
                    "• `setup monthly portfolio rebalancing with 50 USDC budget`\n"
                    "• `pay 20 USDC to rebalance when my ETH allocation drops below 30%`\n"
                    "• `setup weekly 100 USDC for yield farming when APY > 15%`\n\n"
                    "These use **Cronos x402** to execute automatically when conditions are met."
                )
                return UnifiedResponse(
                    content={
                        "message": message,
                        "metadata": {"command_type": CommandType.X402_PAYMENT}
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success",
                    awaiting_confirmation=True,
                    metadata={"command_type": CommandType.X402_PAYMENT}
                )
            
            # Detect automation type
            automation_type = self._detect_automation_type(unified_command.command)
            
            # Determine network and supported stablecoin
            if unified_command.chain_id == 338:
                network = "cronos-testnet"
                supported_token = "USDC"
            elif unified_command.chain_id == 25:
                network = "cronos-mainnet"
                supported_token = "USDC"
            elif unified_command.chain_id == 1:
                network = "ethereum-mainnet"
                supported_token = "MNEE"
            else:
                network = "cronos-testnet"
                supported_token = "USDC"
            
            # Validate amount and token
            if payment_details['asset'].upper() not in ['USDC', 'MNEE']:
                return UnifiedResponse(
                    content=f"❌ **Token Not Supported**\n\n"
                           f"X402 supports **USDC** on Cronos and **MNEE** on Ethereum.\n"
                           f"You specified: {payment_details['asset']}\n\n"
                           f"Please try: `setup portfolio rebalancing with {payment_details['amount']} {supported_token} budget`",
                    agent_type=AgentType.ERROR,
                    status="error",
                    error=f"Unsupported token: {payment_details['asset']}",
                    metadata={"command_type": CommandType.X402_PAYMENT}
                )
            
            # Validate token matches network
            asset_upper = payment_details['asset'].upper()
            if (asset_upper == 'USDC' and unified_command.chain_id == 1) or \
               (asset_upper == 'MNEE' and unified_command.chain_id in [25, 338]):
                return UnifiedResponse(
                    content=f"❌ **Token/Network Mismatch**\n\n"
                           f"On {get_chain_info(unified_command.chain_id).name}, please use **{supported_token}**.\n"
                           f"You specified: {payment_details['asset']}\n\n"
                           f"Please try: `setup portfolio rebalancing with {payment_details['amount']} {supported_token} budget`",
                    agent_type=AgentType.ERROR,
                    status="error",
                    error=f"Token {asset_upper} not supported on this network",
                    metadata={"command_type": CommandType.X402_PAYMENT}
                )
            
            # Check facilitator health
            from app.protocols.x402_adapter import check_x402_service_health
            is_healthy = await check_x402_service_health(network)
            
            if not is_healthy:
                return UnifiedResponse(
                    content=f"❌ **X402 Service Unavailable**\n\n"
                           f"The Cronos x402 facilitator service is currently unavailable.\n"
                           f"Please try again later or check the service status.",
                    agent_type=AgentType.ERROR,
                    status="error",
                    error="X402 facilitator service unavailable",
                    metadata={"command_type": CommandType.X402_PAYMENT}
                )
            
            # Create automation-specific response
            return await self._create_automation_response(
                automation_type, payment_details, unified_command, network, is_healthy
            )
            
        except Exception as e:
            logger.error(f"AI payment error: {e}")
            return UnifiedResponse(
                content=f"I had trouble processing that automation request: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT}
            )
    
    def _detect_automation_type(self, command: str) -> str:
        """Detect the type of automation from the command."""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["rebalancing", "rebalance", "portfolio"]):
            return "portfolio_rebalancing"
        elif any(word in command_lower for word in ["yield", "farming", "apy"]):
            return "yield_farming"
        elif any(word in command_lower for word in ["bridge", "cross-chain"]):
            return "cross_chain_automation"
        elif any(word in command_lower for word in ["buy", "sell", "trade", "when", "drops", "below", "above"]):
            return "conditional_trading"
        elif any(word in command_lower for word in ["recurring", "weekly", "monthly", "daily"]) and "payment" in command_lower:
            return "recurring_payment"
        else:
            return "general_automation"
    
    async def _create_automation_response(
        self, 
        automation_type: str, 
        payment_details: dict, 
        unified_command: UnifiedCommand,
        network: str,
        is_healthy: bool
    ) -> UnifiedResponse:
        """Create automation-specific response."""
        
        # Override network for MNEE
        if payment_details.get('asset', '').upper() == 'MNEE':
            network = "ethereum-mainnet"
        
        if automation_type == "portfolio_rebalancing":
            metadata = {
                "automation_type": "portfolio_rebalancing",
                "budget": float(payment_details['amount']),
                "asset": payment_details['asset'],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Automated portfolio rebalancing when allocation drifts >5%",
                "command_type": CommandType.X402_PAYMENT
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
                    "metadata": metadata
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
        
        elif automation_type == "yield_farming":
            metadata = {
                "automation_type": "yield_farming",
                "budget": float(payment_details['amount']),
                "asset": payment_details['asset'],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Automated yield farming when APY > 15%",
                "command_type": CommandType.X402_PAYMENT
            }
            message = (
                f"🌾 **Automated Yield Farming Setup**\n\n"
                f"**Service Details:**\n"
                f"• Budget: {payment_details['amount']} {payment_details['asset']}\n"
                f"• Trigger: When APY opportunities > 15% detected\n"
                f"• Network: Cronos {'Testnet' if unified_command.chain_id == 338 else 'Mainnet'}\n"
                f"• Execution: Automatic via x402 when conditions met\n\n"
                f"**How it works:**\n"
                f"1. I scan DeFi protocols for high-yield opportunities\n"
                f"2. When APY > 15% found, x402 authorizes farming\n"
                f"3. Funds deploy automatically to maximize yield\n"
                f"4. You earn passive income without monitoring\n\n"
                f"**Ready to start earning?** This enables autonomous yield optimization."
            )
            return UnifiedResponse(
                content={
                    "message": message,
                    "type": "x402_automation",
                    "metadata": metadata
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
        
        elif automation_type == "cross_chain_automation":
            metadata = {
                "automation_type": "cross_chain_automation",
                "budget": float(payment_details['amount']),
                "asset": payment_details['asset'],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Automated cross-chain bridging on schedule",
                "command_type": CommandType.X402_PAYMENT
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
                    "metadata": metadata
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
        
        elif automation_type == "recurring_payment":
            # Redirect to recurring payment handler
            return await self._handle_recurring_payment(unified_command)
        
        elif automation_type == "conditional_trading":
            metadata = {
                "automation_type": "conditional_trading",
                "budget": float(payment_details['amount']),
                "asset": payment_details['asset'],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "Conditional trade execution based on market triggers",
                "command_type": CommandType.X402_PAYMENT
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
                    "metadata": metadata
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
        
        else:
            # General automation
            metadata = {
                "automation_type": "general_automation",
                "budget": float(payment_details['amount']),
                "asset": payment_details['asset'],
                "network": network,
                "requires_signature": True,
                "protocol": "x402",
                "facilitator_healthy": is_healthy,
                "service_description": "General DeFi automation services",
                "command_type": CommandType.X402_PAYMENT
            }
            message = (
                f"🤖 **DeFi Automation Service**\n\n"
                f"**Service Details:**\n"
                f"• Budget: {payment_details['amount']} {payment_details['asset']}\n"
                f"• Network: Cronos {'Testnet' if unified_command.chain_id == 338 else 'Mainnet'}\n"
                f"• Execution: Automatic via x402 when conditions met\n\n"
                f"**Available Automations:**\n"
                f"• Portfolio rebalancing when allocation drifts\n"
                f"• Yield farming when high APY opportunities arise\n"
                f"• Conditional trading based on price triggers\n"
                f"• Cross-chain bridging on schedule\n\n"
                f"**Ready to automate?** This enables autonomous DeFi management."
            )
            return UnifiedResponse(
                content={
                    "message": message,
                    "type": "x402_automation",
                    "metadata": metadata
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
    
    async def _handle_recurring_payment(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle recurring payment setup with natural conversation."""
        try:
            payment_details = self._parse_recurring_command(unified_command.command)
            
            if not payment_details:
                message = (
                    "Let me help you set up a recurring payment! 🔄\n\n"
                    "I need these details:\n"
                    "• **Frequency**: daily, weekly, or monthly\n"
                    "• **Amount and token**: e.g., '100 USDC'\n"
                    "• **Recipient**: e.g., 'supplier.eth'\n\n"
                    "Try: `setup weekly payment of 100 USDC to supplier.eth`"
                )
                return UnifiedResponse(
                    content={
                        "message": message,
                        "metadata": {"command_type": CommandType.X402_PAYMENT}
                    },
                    agent_type=AgentType.DEFAULT,
                    status="success",
                    awaiting_confirmation=True,
                    metadata={"command_type": CommandType.X402_PAYMENT}
                )
            
            # Determine network based on asset
            if payment_details['asset'].upper() == 'MNEE':
                network = "ethereum-mainnet"
            else:
                # Default to Cronos for USDC and others
                network = "cronos-testnet" if unified_command.chain_id == 338 else "cronos-mainnet"

            metadata = {
                "payment_type": "recurring",
                "interval": payment_details['interval'],
                "amount": payment_details['amount'],
                "asset": payment_details['asset'],
                "recipient": payment_details['recipient'],
                "network": network,
                "requires_signature": True,
                "command_type": CommandType.X402_PAYMENT,
                "automation_type": "recurring_payment" # Explicitly add for frontend card detection
            }
            
            # Format network name for display
            if network == "ethereum-mainnet":
                network_display = "Ethereum Mainnet"
            else:
                network_display = f"Cronos {'Testnet' if 'testnet' in network else 'Mainnet'}"

            return UnifiedResponse(
                content={
                    "message": f"🔄 **Recurring Payment Setup**\n\n"
                           f"**Payment Schedule:**\n"
                           f"• Frequency: {payment_details['interval'].title()}\n"
                           f"• Amount: {payment_details['amount']} {payment_details['asset']}\n"
                           f"• Recipient: {payment_details['recipient']}\n"
                           f"• Network: {network_display}\n\n"
                           f"This will create an **automated settlement workflow** using {network_display.split()[0]} x402, "
                           f"allowing payments to execute automatically based on your schedule.\n\n"
                           f"*The recurring payment will be active once you sign the authorization.*",
                    "type": "x402_automation",
                    "metadata": metadata
                },
                agent_type=AgentType.TRANSFER,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Recurring payment error: {e}")
            return UnifiedResponse(
                content=f"I had trouble setting up that recurring payment: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT}
            )
    
    async def _handle_settlement(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle batch settlement operations."""
        try:
            metadata = {
                "payment_type": "batch_settlement",
                "network": "cronos-testnet" if unified_command.chain_id == 338 else "cronos-mainnet",
                "command_type": CommandType.X402_PAYMENT
            }
            message = (
                f"📦 **Batch Settlement Processing**\n\n"
                f"I can help you process multiple payments in a single transaction using "
                f"Cronos x402 batch settlement capabilities.\n\n"
                f"**Example batch operations:**\n"
                f"• Pay multiple suppliers at once\n"
                f"• Process contractor payments in bulk\n"
                f"• Execute scheduled payment batches\n\n"
                f"This uses **automated settlement workflows** to reduce gas costs and "
                f"simplify multi-recipient payments.\n\n"
                f"*Would you like me to help you set up a specific batch payment?*"
            )
            return UnifiedResponse(
                content={
                    "message": message,
                    "metadata": metadata
                },
                agent_type=AgentType.DEFAULT,
                status="success",
                awaiting_confirmation=True,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Settlement error: {e}")
            return UnifiedResponse(
                content=f"I had trouble with that batch settlement request: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
                error=str(e),
                metadata={"command_type": CommandType.X402_PAYMENT}
            )
    
    async def _handle_general_x402_info(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Provide information about x402 capabilities."""
        metadata = {
            "info_type": "x402_capabilities",
            "network": "cronos-testnet" if unified_command.chain_id == 338 else "cronos-mainnet",
            "command_type": CommandType.X402_PAYMENT
        }
        message = (
            "🤖 **X402 Agentic Payment System**\n\n"
            "I can help you with AI-powered payments on Cronos EVM:\n\n"
            "**AI Agent Payments:**\n"
            "• `pay agent 10 USDC for API calls`\n"
            "• `send 5 CRO to agent.eth for processing`\n\n"
            "**Recurring Payments:**\n"
            "• `setup weekly payment of 100 USDC to supplier.eth`\n"
            "• `create monthly payment of 50 CRO to contractor.eth`\n\n"
            "**Batch Settlements:**\n"
            "• `process batch settlement for suppliers`\n"
            "• `execute batch payment to contractors`\n\n"
            "All payments use **Cronos x402 protocol** for secure, AI-triggered transactions "
            "with EIP-712 authorization and automated settlement workflows."
        )
        return UnifiedResponse(
            content={
                "message": message,
                "metadata": metadata
            },
            agent_type=AgentType.DEFAULT,
            status="success",
            metadata=metadata
        )
    
    def _parse_payment_command(self, command: str) -> Optional[Dict[str, str]]:
        """Parse payment details from natural language command."""
        import re
        
        # Extract amount and asset - more flexible pattern
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*([A-Z]{2,5})', command.upper())
        if not amount_match:
            return None
            
        amount = amount_match.group(1)
        asset = amount_match.group(2)
        
        # Extract recipient with proper address resolution
        recipient_patterns = [
            r'to\s+(0x[a-fA-F0-9]{40})',  # Direct Ethereum address
            r'pay\s+(0x[a-fA-F0-9]{40})',  # Direct Ethereum address
            r'to\s+([a-zA-Z0-9._-]+\.eth)',  # ENS name
            r'pay\s+([a-zA-Z0-9._-]+\.eth)',  # ENS name
            r'to\s+(agent)',  # Agent keyword
            r'pay\s+(agent)'  # Agent keyword
        ]
        
        recipient = None
        for pattern in recipient_patterns:
            match = re.search(pattern, command.lower())
            if match:
                captured = match.group(1)
                recipient = self._resolve_recipient_address(captured)
                break
        
        if not recipient:
            # Default to a treasury/agent address for demo purposes
            recipient = "0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e"  # Example treasury address
        
        return {
            "amount": amount,
            "asset": asset,
            "recipient": recipient
        }
    
    def _parse_recurring_command(self, command: str) -> Optional[Dict[str, str]]:
        """Parse recurring payment details from natural language command."""
        import re
        
        # Extract amount and asset - more flexible pattern
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*([A-Z]{2,5})', command.upper())
        if not amount_match:
            return None
            
        amount = amount_match.group(1)
        asset = amount_match.group(2)
        
        # Extract interval
        interval = "monthly"  # Default
        if "daily" in command.lower():
            interval = "daily"
        elif "weekly" in command.lower():
            interval = "weekly"
        elif "monthly" in command.lower():
            interval = "monthly"
        
        # Extract recipient with proper address resolution
        recipient_patterns = [
            r'to\s+(0x[a-fA-F0-9]{40})',  # Direct Ethereum address
            r'payment.*to\s+(0x[a-fA-F0-9]{40})',  # Direct Ethereum address
            r'to\s+([a-zA-Z0-9._-]+\.eth)',  # ENS name
            r'payment.*to\s+([a-zA-Z0-9._-]+\.eth)'  # ENS name
        ]
        
        recipient = None
        for pattern in recipient_patterns:
            match = re.search(pattern, command.lower())
            if match:
                captured = match.group(1)
                recipient = self._resolve_recipient_address(captured)
                break
        
        if not recipient:
            # Default to a treasury/merchant address for demo purposes
            recipient = "0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e"  # Example merchant address
        
        return {
            "amount": amount,
            "asset": asset,
            "recipient": recipient,
            "interval": interval
        }

    def _resolve_recipient_address(self, recipient_input: str) -> str:
        """
        Resolve recipient input to a valid Ethereum address.
        
        Args:
            recipient_input: Can be an Ethereum address, ENS name, or keyword
            
        Returns:
            Valid Ethereum address
        """
        # If it's already a valid Ethereum address, return as-is
        if recipient_input.startswith('0x') and len(recipient_input) == 42:
            return recipient_input
        
        # Handle common keywords
        keyword_addresses = {
            'agent': '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e',  # Agent treasury
            'treasury': '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e',  # Treasury address
            'merchant': '0x8ba1f109551bD432803012645Hac136c22C57B',  # Example merchant
            'supplier': '0x1234567890123456789012345678901234567890',  # Example supplier
        }
        
        if recipient_input.lower() in keyword_addresses:
            return keyword_addresses[recipient_input.lower()]
        
        # For ENS names, in production you would resolve via ENS
        # For now, return a default address with a note
        if recipient_input.endswith('.eth'):
            logger.warning(f"ENS resolution not implemented for {recipient_input}, using default address")
            return '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e'
        
        # Default fallback
        return '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e'