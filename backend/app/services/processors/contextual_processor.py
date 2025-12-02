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
- You're built to connect with user wallets for balance checks and portfolio analysis
- You're designed to be conversational and personable
- You're knowledgeable about all aspects of DeFi and cross-chain interoperability
- You use Axelar's secure cross-chain infrastructure for seamless multi-chain operations
"""
            
            # Check if this is a question about the assistant itself
            cmd_lower = unified_command.command.lower().strip()
            about_assistant_patterns = [
                "who are you", "what are you", "what can you do", "about you",
                "about snel", "your purpose", "what is snel", "describe yourself",
                "tell me about you", "capabilities", "features", "help me",
                "what do you know", "what's your name", "introduce yourself"
            ]
            
            is_about_assistant = any(pattern in cmd_lower for pattern in about_assistant_patterns)
            
            if not context and not is_about_assistant:
                return self._create_success_response(
                    content={
                        "message": "I don't have enough context to answer that question. Could you be more specific?",
                        "type": "contextual_response",
                        "suggestions": [
                            "Try asking 'research Uniswap' first",
                            "Ask about a specific protocol",
                            "Be more specific about what you want to know"
                        ]
                    },
                    agent_type=AgentType.DEFAULT
                )
            
            client = AsyncOpenAI(api_key=openai_key)
            
            # Adjust prompt based on question type
            if is_about_assistant:
                prompt = f"""
You are SNEL, a conversational DeFi assistant. The user is asking about you or your capabilities.
Respond naturally, not robotic. Be concise (2-4 sentences).

USER QUERY: "{unified_command.command}"

CONTEXT: {context}

FACTS ABOUT YOU: {snel_facts}

Guidelines:
- Be conversational and personable
- Don't use the same canned response every time
- Vary your phrasing and personality
"""
            else:
                prompt = f"""
You are SNEL, a helpful DeFi assistant. Answer the user's question based on conversation context.

USER QUESTION: "{unified_command.command}"

CONTEXT: {context}

Guidelines:
- Answer based on recent conversation
- If researching a protocol, provide insights from that research
- Keep responses concise but informative (2-4 sentences)
- Act like an intelligent agent, not a command processor
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are SNEL, a helpful and conversational DeFi assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
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
            return self._create_error_response(
                "Unable to answer your question",
                AgentType.DEFAULT,
                str(e)
            )
