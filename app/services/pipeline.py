from typing import Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.dca_agent import DCAAgent
import re
import json
import random

logger = logging.getLogger(__name__)

class Pipeline(BaseModel):
    """Pipeline for processing commands and queries."""
    token_service: TokenService
    swap_agent: SimpleSwapAgent
    price_agent: PriceAgent
    dca_agent: Optional[DCAAgent] = None
    redis_service: Optional[RedisService] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize DCA agent if not provided
        if self.dca_agent is None:
            self.dca_agent = DCAAgent(
                token_service=self.token_service,
                redis_service=self.redis_service
            )
        logger.info("Pipeline initialized with all agents")

    async def process(self, input_text: str, chain_id: Optional[int] = None, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process input text and route to the appropriate agent.
        
        Args:
            input_text: The user's input text
            chain_id: The blockchain chain ID
            wallet_address: The user's wallet address
            
        Returns:
            Response from the appropriate agent
        """
        logger.info(f"Processing input: {input_text}")
        
        # Normalize input text
        normalized_text = input_text.lower().strip()
        
        # Check if this is a DCA command
        is_dca_command = (
            normalized_text.startswith("dca ") or
            normalized_text.startswith("dollar cost average ") or
            re.search(r"\b(please|can you|can we|can i|could you|i want to|setup|set up)\s+dca\b", normalized_text) is not None or
            ("dca" in normalized_text and any(token in normalized_text for token in ["eth", "usdc", "dai", "usdt", "$"])) or
            ("dollar cost average" in normalized_text)
        )
        
        # Check if this is a swap command
        is_swap_command = (
            normalized_text.startswith("swap") or
            normalized_text.startswith("approved:") or
            ("swap" in normalized_text and any(token in normalized_text for token in ["eth", "usdc", "dai", "usdt", "$"])) or
            ("convert" in normalized_text and any(token in normalized_text for token in ["eth", "usdc", "dai", "usdt", "$"]))
        )
        
        # Check if this is a price query
        is_price_query = (
            normalized_text.startswith("price ") or
            normalized_text.startswith("p ") or
            "price" in normalized_text or 
            "how much" in normalized_text or
            "worth" in normalized_text or
            "value" in normalized_text or
            "cost" in normalized_text or
            ("what is" in normalized_text and any(token in normalized_text for token in ["eth", "btc", "usdc", "dai", "usdt", "bitcoin", "ethereum", "token", "coin", "crypto"]))
        )
        
        # Try to process as a DCA command first
        if is_dca_command:
            try:
                logger.info("Processing as DCA command")
                result = await self.dca_agent.process_dca_command(
                    input_text, 
                    chain_id=chain_id,
                    wallet_address=wallet_address
                )
                if not result.get("error"):
                    # Successfully processed as DCA
                    result["agent_type"] = "dca"
                    # Make sure the content type is set correctly
                    if "content" in result and isinstance(result["content"], dict) and "type" not in result["content"]:
                        result["content"]["type"] = "dca_confirmation"
                    return result
                else:
                    logger.warning(f"DCA processing failed: {result.get('error')}")
                    # Fall through to other processing
            except Exception as e:
                logger.error(f"Error processing DCA command: {e}")
                # Fall through to other processing
        
        # Try to process as a swap command
        if is_swap_command:
            try:
                logger.info("Processing as swap command")
                result = await self.swap_agent.process_swap_command(input_text, chain_id)
                if not result.get("error"):
                    # Successfully processed as swap
                    result["agent_type"] = "swap"
                    # Make sure the content type is set correctly
                    if "content" in result and isinstance(result["content"], dict) and "type" not in result["content"]:
                        result["content"]["type"] = "swap_confirmation"
                    return result
                else:
                    logger.warning(f"Swap processing failed: {result.get('error')}")
                    # Fall through to price query
            except Exception as e:
                logger.error(f"Error processing swap command: {e}")
                # Fall through to price query
        
        # Try to process as a price query
        if is_price_query:
            logger.info("Processing as price query")
            try:
                result = await self.price_agent.process_price_query(input_text, chain_id)
                if not result.get("error"):
                    # If there's a message in the content, use it directly
                    if "content" in result and "message" in result["content"]:
                        result["content"]["type"] = "message"
                        result["agent_type"] = "price"
                        return result
                    # Otherwise, format a simple response
                    elif "content" in result and "price" in result["content"]:
                        price_data = result["content"]
                        result["content"] = {
                            "type": "message",
                            "message": f"The current price of {price_data['token']['symbol']} is ${price_data['price']:.2f}."
                        }
                        result["agent_type"] = "price"
                        return result
                    else:
                        result["agent_type"] = "price"
                        return result
                else:
                    logger.warning(f"Price query processing failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"Error processing price query: {str(e)}")
        
        # Process as a general query
        logger.info("Processing as general query")
        
        # Extract token name if present
        token_match = re.search(r'\b(eth|btc|usdc|dai|usdt|bitcoin|ethereum)\b', normalized_text)
        token_name = token_match.group(1) if token_match else None
        
        # Add some personality to the responses
        greetings = ["gm", "good morning", "hello", "hi", "hey", "howdy", "sup", "yo"]
        if any(greeting in normalized_text for greeting in greetings):
            response = {
                "content": {
                    "type": "message",
                    "message": self._get_greeting_response()
                },
                "agent_type": "general"
            }
        elif "help" in normalized_text or "what can you do" in normalized_text:
            response = {
                "content": {
                    "type": "message",
                    "message": self._get_help_response()
                },
                "agent_type": "general"
            }
        elif token_name and ("what" in normalized_text or "tell me about" in normalized_text):
            response = {
                "content": {
                    "type": "message",
                    "message": f"You're asking about {token_name.upper()}? I'm a bit lazy to look that up right now. Try asking for the price with 'price {token_name}' instead!"
                },
                "agent_type": "general"
            }
        else:
            response = {
                "content": {
                    "type": "message",
                    "message": self._get_random_response(input_text)
                },
                "agent_type": "general"
            }
        
        return response
    
    def _get_greeting_response(self) -> str:
        """Get a random greeting response with personality."""
        greetings = [
            "gm fren! Ready to ape into some tokens today?",
            "Hey there! I'm feeling particularly lazy today, but I'll try to help.",
            "Oh hi! You caught me in the middle of my crypto nap.",
            "Sup! I'm your friendly neighborhood pointless agent. What's on your mind?",
            "Hello! I'm here to pretend I know what I'm doing with your crypto.",
            "Hey hey hey! Another day, another opportunity to lose money together!",
            "Greetings, human! I'm here to assist with all your crypto needs... or at least pretend to.",
            "Yo! Let's make some questionable financial decisions today!",
            "Hi there! I'm your AI assistant, but don't expect too much. I'm pretty lazy.",
            "Hello! I'm here to help you navigate the wild world of crypto... or just chat about the weather."
        ]
        return random.choice(greetings)
    
    def _get_help_response(self) -> str:
        """Get a help response with personality."""
        return (
            "I'm your super pointless lazy agent, but I can still help with a few things:\n\n"
            "1. Check token prices: 'price ETH' or 'what's the price of Bitcoin?'\n"
            "2. Swap tokens: 'swap 1 ETH for USDC' or 'convert 100 USDC to ETH'\n"
            "3. Set up DCA orders: 'dca $10 USDC into ETH over 5 days'\n\n"
            "Just don't expect me to be too enthusiastic about it. I'm pretty lazy, you know."
        )
    
    def _get_random_response(self, input_text: str) -> str:
        """Get a random response with personality."""
        responses = [
            f"I heard you say '{input_text}', but I'm too lazy to figure out what that means. Try asking for a price, swap, or DCA?",
            "That's cool and all, but have you tried asking me something I actually know about? Like token prices or swaps?",
            "Hmm, not sure what to do with that. I'm pretty pointless, but I can help with prices, swaps, and DCA orders!",
            "I'd love to help, but that's outside my very limited skill set. Try asking about crypto prices or swaps instead?",
            f"'{input_text}'? That's nice, but I'm more into token swaps and price checks. Want to try one of those?",
            "I'm just a pointless agent pretending to be useful. Maybe try asking for a token price or setting up a swap?",
            "I'm feeling particularly lazy today. Can you ask me something easier, like a token price or swap?",
            "That's beyond my pointless existence. But I can check prices, swap tokens, or set up DCA orders!",
            "I'm not smart enough for that. But I can pretend to be smart about crypto prices and swaps!",
            "I'm just a simple crypto agent with simple needs. Ask me about prices, swaps, or DCA orders instead."
        ]
        return random.choice(responses)
