"""
Contextual command processor.
Handles questions, greetings, and general DeFi-related queries.
"""
import logging
import os
from openai import AsyncOpenAI

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, CommandType
)
from app.services.chat_history import chat_history_service
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class ContextualProcessor(BaseProcessor):
    """Processes contextual questions and greetings."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process contextual command.
        
        Routes to appropriate handler based on command type:
        - GREETING: Simple hello responses
        - CONTEXTUAL_QUESTION: Questions about assistant, protocols, DeFi
        - PROTOCOL_RESEARCH: Research requests about specific DeFi protocols
        """
        if unified_command.command_type == CommandType.GREETING:
            return await self._handle_greeting(unified_command)
        elif unified_command.command_type == CommandType.CONTEXTUAL_QUESTION:
            return await self._handle_contextual_question(unified_command)
        else:
            return await self._handle_contextual_question(unified_command)
    
    async def _handle_greeting(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle simple greetings with fast cached responses."""
        try:
            # Get recent conversation context
            context = chat_history_service.get_recent_context(
                unified_command.wallet_address,
                unified_command.user_name,
                num_messages=5
            )
            
            # If it's a simple greeting (one or two words), use canned responses for speed
            cmd_lower = unified_command.command.lower().strip()
            simple_greetings = {
                "gm": "Good morning! How can I help you with crypto today?",
                "good morning": "Good morning! How can I help you with crypto today?",
                "hello": "Hello there! How can I assist you with crypto today?",
                "hi": "Hi! How can I help you with crypto today?",
                "hey": "Hey there! How can I assist you with crypto today?",
                "howdy": "Howdy! How can I help you with crypto today?",
                "sup": "Sup! How can I assist you with crypto today?",
                "yo": "Yo! How can I help you with crypto today?"
            }
            
            if cmd_lower in simple_greetings:
                return self._create_success_response(
                    content={
                        "message": simple_greetings[cmd_lower],
                        "type": "greeting"
                    },
                    agent_type=AgentType.DEFAULT
                )
            
            # For more complex greetings, use AI
            return await self._generate_greeting_response(unified_command)
            
        except Exception as e:
            logger.exception(f"Error handling greeting: {e}")
            return self._create_error_response(
                "Unable to process greeting",
                AgentType.DEFAULT,
                str(e)
            )
    
    async def _generate_greeting_response(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Generate greeting response using AI."""
        try:
            openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return self._create_error_response(
                    "OpenAI API key not available",
                    AgentType.DEFAULT
                )
            
            # Get recent conversation context
            context = chat_history_service.get_recent_context(
                unified_command.wallet_address,
                unified_command.user_name,
                num_messages=5
            )
            
            client = AsyncOpenAI(api_key=openai_key)
            
            prompt = f"""
You are SNEL, a friendly DeFi assistant. The user has greeted you.
Respond with a warm, natural greeting that acknowledges what they said.

USER MESSAGE: "{unified_command.command}"

RECENT CONTEXT:
{context}

Keep your response brief (1-2 sentences) and friendly.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are SNEL, a friendly DeFi assistant. Respond naturally to greetings."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            return self._create_success_response(
                content={
                    "message": ai_response,
                    "type": "greeting"
                },
                agent_type=AgentType.DEFAULT
            )
            
        except Exception as e:
            logger.exception(f"Error generating greeting: {e}")
            return self._create_error_response(
                "Unable to generate greeting",
                AgentType.DEFAULT,
                str(e)
            )
    
    async def _handle_contextual_question(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """Handle contextual questions using AI and conversation history."""
        try:
            openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return self._create_error_response(
                    "OpenAI API key not available",
                    AgentType.DEFAULT
                )
            
            # Get recent conversation context
            context = chat_history_service.get_recent_context(
                unified_command.wallet_address,
                unified_command.user_name,
                num_messages=10
            )
            
            # Set of facts about SNEL for the LLM
            snel_facts = """
- You are SNEL — Smart, Natural, Efficient, Limitless DeFi Assistant
- You help with stablecoin information and RWA insights
- You provide risk assessment and portfolio diversification advice
- You deliver real-time market data
- You assist with DeFi operations like swaps and bridges
- You specialize in cross-chain operations using Axelar Network's General Message Passing (GMP)
- You can execute complex cross-chain swaps, yield farming, and liquidity provision across 16+ blockchain networks
- You handle multi-step cross-chain operations with natural language commands

PRIVACY FEATURES YOU ENABLE:
- **Privacy Bridging to Zcash**: Bridge assets from any supported chain (Ethereum, Base, Polygon, Arbitrum, etc.) to Zcash for private transactions
- **Shielded Transactions**: Zcash uses zero-knowledge proofs to hide transaction details (sender, receiver, amount)
- **Unified Addresses (UA)**: Modern Zcash addresses that work across all pools (shielded and transparent)
- **Encrypted Transaction History**: Your transaction history is only visible to you, not publicly on the blockchain
- **Confidential Amounts**: Transaction amounts are encrypted and hidden from public view
- **Private Memos**: Send encrypted messages with your transactions that only the recipient can read
- **Anonymity Set**: Larger privacy pools mean better anonymity as your transaction blends with others

HOW PRIVACY WORKS:
- Bridge assets to Zcash using Axelar's secure cross-chain protocol
- Receive funds in a shielded address (recommended wallets: Zashi mobile, Nighthawk desktop)
- All transaction details (addresses, amounts, memos) are encrypted using zero-knowledge proofs
- Only you can view your transaction history with your viewing key
- Transactions are mathematically verified without revealing private information

PRIVACY OPERATIONS (Zcash Integration):
- You support PRIVACY BRIDGING: Bridge assets to Zcash for enhanced transaction privacy
- Zcash uses shielded addresses to hide transaction details (addresses, amounts, history)
- Users can bridge from public chains (Ethereum, Polygon, Base, Arbitrum, etc.) to Zcash
- Recommended Zcash wallets: Zashi (mobile), Nighthawk (desktop) - both shielded by default
- After bridging, users receive private funds in a unified address (UA)
- Privacy is opt-in to shielded addresses; transparent transactions still supported
- Axelar GMP handles the cross-chain bridge securely
- Users can spend bridged Zcash at merchants or send privately to others

PRIVACY GUIDANCE FOR USERS:
- Always recommend wallets that are "shielded by default"
- Emphasize that transaction amounts and addresses are encrypted
- Explain that larger privacy pools = better anonymity
- Mention security: backup phrases, trusted wallet sources, secure receiving addresses
- Provide next steps after bridging: get wallet, receive funds, use privately

MNEE STABLECOIN FEATURES YOU SUPPORT:
- **What is MNEE**: A programmable USD-backed stablecoin designed for AI agents, commerce, and automated finance
- **Core Capabilities**: 
  - AI Agent Payments: Autonomous MNEE transactions for services and subscriptions
  - Commerce Payments: Support for invoices, purchase orders, and business-to-business transactions with memo fields
  - DeFi Integration: Compatible with DEX aggregators, lending protocols, and automated market makers
- **Use Cases**:
  - Pay $100 MNEE to merchant.eth with invoice references (e.g., "for order #1234")
  - Autonomous agent-to-agent settlement for services
  - Programmable payments with custom metadata and conditions
  - Cross-chain settlement via Axelar GMP
- **Key Benefits**:
  - Stable value (1 MNEE = $1 USD)
  - Programmable features for business automation
  - Seamless integration with DeFi protocols
  - Natural language payment commands

AUTOMATED DEFI SERVICES YOU ENABLE:
- **Portfolio Rebalancing**: "setup monthly portfolio rebalancing with 50 USDC budget" - automatically rebalances when allocation drifts >5%
- **Yield Farming**: "setup weekly 100 USDC for yield farming when APY > 15%" - deploys funds to high-yield opportunities automatically
- **Conditional Trading**: "pay 20 USDC to buy ETH when price drops below $3000" - executes trades based on market conditions
- **Cross-Chain Automation**: "setup daily bridge of 50 USDC to Polygon for gas" - automated cross-chain operations
- **Recurring Subscriptions**: "setup monthly 25 USDC payment to service.eth" - automated subscription management

X402 AGENTIC PAYMENT FEATURES YOU SUPPORT:
- **What is X402**: Cronos protocol for AI-triggered payments and automated settlement workflows
- **Core Capabilities**:
  - AI Agent Payments: Autonomous payments triggered by AI conditions on Cronos EVM
  - Automated Settlement: Recurring and batch payments with smart contract authorization
  - Programmable Authorization: EIP-712 signatures for secure payment delegation
  - Agent-to-Agent Transactions: Direct AI-to-AI settlement without human intervention
- **Automated DeFi Services**:
  - Portfolio Rebalancing: "setup monthly portfolio rebalancing with 50 USDC budget" - automatically rebalances when allocation drifts >5%
  - Yield Farming: "setup weekly 100 USDC for yield farming when APY > 15%" - deploys funds to high-yield opportunities
  - Conditional Trading: "pay 20 USDC to buy ETH when price drops below $3000" - executes trades based on market conditions
  - Cross-Chain Automation: "setup daily bridge of 50 USDC to Polygon for gas" - automated cross-chain operations
- **Use Cases**:
  - "pay agent 10 USDC for API calls" - AI service payments
  - "setup weekly payment of 100 USDC to supplier.eth" - Recurring business payments
  - "process batch settlement for contractors" - Multi-recipient payments
  - Conditional payments based on oracle data or smart contract states
- **Key Benefits**:
  - Works on Cronos EVM (mainnet and testnet)
  - Gasless transactions via EIP-7702 delegation
  - Secure cryptographic authorization
  - Natural language command interface
  - Integration with existing DeFi protocols

- You're built to connect with user wallets for balance checks and portfolio analysis
- You're designed to be conversational and personable
- You're knowledgeable about all aspects of DeFi and cross-chain interoperability
- You use Axelar's secure cross-chain infrastructure for seamless multi-chain operations
- You support MNEE commerce payments with natural language commands
- You support X402 agentic payments on Cronos EVM for AI-triggered transactions
"""
            
            # Check if this is a question about the assistant itself
            cmd_lower = unified_command.command.lower().strip()
            about_assistant_patterns = [
                "who are you", "what are you", "what can you do", "about you",
                "about snel", "your purpose", "what is snel", "describe yourself",
                "tell me about you", "capabilities", "features", "help me",
                "what do you know", "what's your name", "introduce yourself",
                "private", "privacy", "private transaction", "stuff in private",
                "privacy features", "privacy feature", "enable", "support",
                "what privacy", "how private", "make private", "keep private",
                "anonymous", "anonymity", "confidential", "secure transaction",
                "mnee", "stablecoin", "commerce payment", "programmatic money",
                "x402", "agentic payment", "ai payment", "automated payment",
                "agent payment", "recurring payment", "batch settlement",
                "cronos", "ethereum", "base", "polygon", "arbitrum", "chain", "network",
                "what can i do", "how do i", "tell me about", "what can you",
                "help with", "info", "information"
            ]
            
            is_about_assistant = any(pattern in cmd_lower for pattern in about_assistant_patterns)
            
            if not context and not is_about_assistant:
                # Check if this might be a blockchain or crypto query that should go to AI anyway
                crypto_keywords = ["crypto", "bitcoin", "ethereum", "eth", "cronos", "cro", "defi", "web3", "wallet", "token", "coin"]
                is_crypto_query = any(keyword in cmd_lower for keyword in crypto_keywords)
                
                if not is_crypto_query:
                    # Check if this might be a payment or transaction command that was misclassified
                    cmd_lower = unified_command.command.lower()
                    payment_keywords = ["payment", "pay", "send", "transfer", "bridge", "swap", "setup", "recurring", "monthly", "weekly", "daily"]
                    
                    if any(keyword in cmd_lower for keyword in payment_keywords):
                        return self._create_success_response(
                            content={
                                "message": "I can help with that! Could you be more specific about what you'd like to do? For example:\n• `setup monthly payment of 100 USDC to supplier.eth`\n• `send 50 MNEE to merchant.eth`\n• `bridge 100 USDC to Polygon`",
                                "type": "contextual_response",
                                "suggestions": [
                                    "Try being more specific about amounts and recipients",
                                    "Include token symbols (USDC, MNEE, ETH, etc.)",
                                    "Specify the recipient address or ENS name"
                                ]
                            },
                            agent_type=AgentType.DEFAULT
                        )
                    
                    return self._create_success_response(
                        content={
                            "message": "I don't have enough context to answer that question. Could you be more specific about what you're interested in?",
                            "type": "contextual_response",
                            "suggestions": [
                                "Try asking 'what can I do on Cronos?'",
                                "Ask about a specific DeFi protocol",
                                "Be more specific about what you want to know"
                            ]
                        },
                        agent_type=AgentType.DEFAULT
                    )
                # If it IS a crypto query, fall through to AI handling
            
            client = AsyncOpenAI(api_key=openai_key)
            
            # Adjust prompt based on question type
            if is_about_assistant:
                prompt = f"""
You are SNEL, a conversational DeFi assistant. The user is asking about you or your capabilities.
Respond naturally and concisely. Keep it minimal - 1-2 sentences max.

USER QUERY: "{unified_command.command}"

CONTEXT: {context}

FACTS ABOUT YOU: {snel_facts}

Guidelines:
- Be conversational and personable
- Keep responses SHORT and to the point (1-2 sentences)
- Don't list everything - just highlight key points
- Users can ask follow-ups if they want more details
- Vary your phrasing naturally
"""
            else:
                prompt = f"""
You are SNEL, a helpful DeFi assistant. Answer the user's question based on conversation context.

USER QUESTION: "{unified_command.command}"

CONTEXT: {context}

Guidelines:
- Answer based on recent conversation
- If researching a protocol, provide insights from that research
- Keep responses CONCISE and minimal (1-2 sentences)
- Act like an intelligent agent, not a command processor
- Users can ask follow-ups for more details
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are SNEL, a helpful and conversational DeFi assistant. Keep responses concise and minimal."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,  # Reduced from 300 to enforce concise responses
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            return self._create_success_response(
                content={
                    "message": ai_response,
                    "type": "contextual_response"
                },
                agent_type=AgentType.DEFAULT
            )
            
        except Exception as e:
            logger.exception(f"Error handling contextual question: {e}")
            
            # Check if this might be a payment command that was misclassified
            cmd_lower = unified_command.command.lower()
            payment_keywords = ["payment", "pay", "send", "transfer", "bridge", "swap", "setup", "recurring", "monthly", "weekly", "daily"]
            
            if any(keyword in cmd_lower for keyword in payment_keywords):
                return self._create_error_response(
                    "I can help with payments and transactions! Try being more specific, like:\n• `setup monthly payment of 100 USDC to supplier.eth`\n• `send 50 MNEE to merchant.eth`\n• `bridge 100 USDC to Polygon`",
                    AgentType.DEFAULT,
                    "Command may have been misclassified as contextual question"
                )
            
            return self._create_error_response(
                "Unable to answer your question",
                AgentType.DEFAULT,
                str(e)
            )
