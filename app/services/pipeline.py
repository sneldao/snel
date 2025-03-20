from typing import Optional, Dict, Any, Union
import logging
from pydantic import BaseModel, Field
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.dca_agent import DCAAgent
from app.agents.brian_agent import BrianAgent
from app.agents.agent_factory import AgentFactory
import re
import json
import random

logger = logging.getLogger(__name__)

class Pipeline(BaseModel):
    """Pipeline for processing commands and queries."""
    token_service: TokenService
    swap_agent: Optional[SimpleSwapAgent] = None
    price_agent: Optional[PriceAgent] = None
    dca_agent: Optional[DCAAgent] = None
    brian_agent: Optional[BrianAgent] = None
    redis_service: Optional[RedisService] = None
    api_key: Optional[str] = None
    alchemy_key: Optional[str] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, **data):
        # Initialize token service with Alchemy key if provided
        if "token_service" not in data and "alchemy_key" in data:
            data["token_service"] = TokenService(alchemy_key=data["alchemy_key"])
            
        super().__init__(**data)
        
        # Initialize agents if not provided
        if self.swap_agent is None:
            self.swap_agent = SimpleSwapAgent(api_key=self.api_key)
            
        if self.price_agent is None:
            try:
                logger.info("Initializing PriceAgent")
                self.price_agent = PriceAgent(api_key=self.api_key)
                logger.info("PriceAgent initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing PriceAgent: {e}")
                from app.agents.base import PointlessAgent
                logger.warning("Falling back to minimal PointlessAgent for prices")
                self.price_agent = PointlessAgent(
                    prompt="You are a helpful assistant that processes price queries for cryptocurrencies.",
                    api_key=self.api_key
                )
                
        if self.dca_agent is None:
            self.dca_agent = DCAAgent(
                token_service=self.token_service,
                redis_service=self.redis_service,
                api_key=self.api_key
            )
            
        if self.brian_agent is None:
            self.brian_agent = BrianAgent(
                token_service=self.token_service,
                redis_service=self.redis_service,
                api_key=self.api_key
            )
        
        logger.info("Pipeline initialized with all agents")
    
    def _get_dca_agent(self) -> DCAAgent:
        """Lazy load DCA agent."""
        if self.dca_agent is None:
            self.dca_agent = DCAAgent(
                token_service=self.token_service,
                redis_service=self.redis_service,
                api_key=self.api_key
            )
        return self.dca_agent
    
    def _get_brian_agent(self) -> BrianAgent:
        """Lazy load Brian agent."""
        if self.brian_agent is None:
            self.brian_agent = BrianAgent(
                token_service=self.token_service,
                redis_service=self.redis_service,
                api_key=self.api_key
            )
        return self.brian_agent
    
    def _get_swap_agent(self) -> SimpleSwapAgent:
        """Lazy load Swap agent."""
        if self.swap_agent is None:
            self.swap_agent = SimpleSwapAgent(api_key=self.api_key)
        return self.swap_agent

    async def process(
        self, 
        command: Union[str, Dict[str, Any]], 
        wallet_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        user_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a command through the agent pipeline."""
        try:
            # If the command is a dict, extract the content
            if isinstance(command, dict):
                if "content" in command:
                    command_text = command["content"]
                else:
                    # If no content field, use the dict as is and let the agent handle it
                    logger.warning("Command is a dict without content field")
                    return await self._process_dict_command(command, wallet_address, chain_id, user_name, settings)
            else:
                command_text = command

            # Check if command is a string before calling lower()
            if isinstance(command_text, str):
                normalized_command = command_text.lower().strip()
            else:
                logger.warning(f"Command is not a string: {type(command_text)}")
                # Convert to string if possible
                try:
                    normalized_command = str(command_text).lower().strip()
                except:
                    # If we can't normalize, just pass the original command to the function
                    return await self._process_dict_command(command, wallet_address, chain_id, user_name, settings)

            # Convert chain_id to int if provided
            chain_id_int = int(chain_id) if chain_id else None
            
            # Handle yes/no confirmations first - these are processed differently
            if normalized_command in ["yes", "y", "yeah", "yep", "ok", "okay", "sure", "confirm"]:
                # Check if there's a pending command for a Brian operation specifically
                if self.redis_service:
                    try:
                        # Try to get the pending command directly
                        pending_data = await self.redis_service.get_pending_command(wallet_address)
                        pending_type = await self.redis_service.get(f"pending_command_type:{wallet_address}")
                        
                        logger.info(f"Found pending command type: {pending_type} for wallet {wallet_address}")
                        
                        if pending_type == "brian" or (pending_data and pending_data.get("is_brian_operation")):
                            logger.info(f"Forwarding confirmation directly to Brian agent for wallet {wallet_address}")
                            brian_agent = self._get_brian_agent()
                            result = await brian_agent.process_brian_confirmation(
                                chain_id=chain_id_int,
                                wallet_address=wallet_address,
                                user_name=user_name
                            )
                            # Add agent type to ensure proper routing
                            if isinstance(result, dict):
                                result["agent_type"] = "brian"
                            return result
                    except Exception as e:
                        logger.error(f"Error processing confirmation: {e}", exc_info=True)
                        return {
                            "content": {
                                "type": "message",
                                "message": f"Error processing confirmation: {str(e)}. Please try your command again."
                            },
                            "error": str(e),
                            "agent_type": "error"
                        }
            
            # Detect bridge command patterns more aggressively - include $ pattern variations
            bridge_patterns = [
                r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+",  # full format
                r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+",  # simple format
                r"bridge\s+\$\d+(?:\.\d+)?\s+(?:of|worth\s+of)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+",  # $ with of
                r"bridge\s+\$\d+(?:\.\d+)?(?:\s+of)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+"  # basic $ format
            ]
            
            is_bridge_command = any(re.search(pattern, normalized_command, re.IGNORECASE) is not None for pattern in bridge_patterns)
            
            # Handle bridge commands with the Brian agent
            if is_bridge_command:
                try:
                    # Log bridge detection
                    for i, pattern in enumerate(bridge_patterns):
                        if re.search(pattern, normalized_command, re.IGNORECASE):
                            logger.info(f"BRIDGE DETECTION: Command '{command_text}' matched pattern {i+1}")
                    
                    logger.info(f"BRIDGE DETECTION: Routing directly to Brian agent: {command_text}")
                    
                    brian_agent = self._get_brian_agent()
                    result = await brian_agent.process_brian_command(
                        command=command_text,
                        chain_id=chain_id_int,
                        wallet_address=wallet_address,
                        user_name=user_name
                    )
                    
                    # Always mark bridge commands as Brian operations for proper follow-up
                    if isinstance(result, dict):
                        result["agent_type"] = "brian"
                        result["is_brian_operation"] = True
                        
                        # Ensure the command is stored for confirmation if needed
                        if self.redis_service and wallet_address:
                            try:
                                is_awaiting = result.get("awaitingConfirmation", False)
                                if is_awaiting:
                                    logger.info(f"Storing bridge command for confirmation: {command_text}")
                                    await self.redis_service.store_pending_command(
                                        wallet_address=wallet_address,
                                        command=command_text, 
                                        is_brian_operation=True
                                    )
                            except Exception as redis_err:
                                logger.error(f"Failed to store bridge command in Redis: {redis_err}")
                    
                    return result
                except Exception as e:
                    logger.error(f"Error processing bridge command: {e}", exc_info=True)
                    return {
                        "content": {
                            "type": "message",
                            "message": f"Error processing bridge command: {str(e)}. Please try again."
                        },
                        "error": str(e),
                        "agent_type": "brian"
                    }
            
            # First, try to identify if this is a swap command
            swap_agent = self._get_swap_agent()
            if not normalized_command.startswith("bridge") and await swap_agent.is_swap_command(command):
                logger.info("Processing swap command")
                try:
                    result = await swap_agent.process_swap_command(command, chain_id)
                    result["agent_type"] = "swap"
                    return result
                except ValueError as e:
                    # Handle common swap command errors with friendly suggestions
                    error_msg = str(e)
                    logger.warning(f"Swap command error: {error_msg}")
                    
                    # Create a user-friendly error message
                    if "Could not parse tokens" in error_msg:
                        friendly_message = "I couldn't understand which tokens you want to swap. "
                        if "Did you mean" in error_msg:
                            # Extract the suggestion if there is one
                            friendly_message += error_msg
                        else:
                            friendly_message += "Try a format like 'swap 0.1 ETH for USDC' or 'swap $10 of ETH into USDC'"
                    elif "No amount found" in error_msg:
                        friendly_message = "I couldn't figure out how much you want to swap. Please specify an amount, like 'swap 0.1 ETH for USDC' or 'swap $10 worth of ETH for USDC'."
                    else:
                        friendly_message = f"I had trouble with your swap request: {error_msg}. Try rephrasing your command."
                    
                    return {
                        "content": {"type": "message", "message": friendly_message},
                        "agent_type": "swap",
                        "error": error_msg
                    }

            # Check if it's a DCA command
            dca_agent = self._get_dca_agent()
            if await dca_agent.is_dca_command(command):
                logger.info("Processing DCA command")
                result = await dca_agent.process_dca_command(command, chain_id, wallet_address)
                result["agent_type"] = "dca"
                return result

            # If not a swap or DCA command, process as generic input
            # This will just fall back to the existing process method
            return await self.process_input(command, chain_id, wallet_address)

        except Exception as e:
            logger.exception(f"Error in pipeline: {e}")
            return {
                "error": str(e),
                "content": {"type": "error", "message": str(e)},
                "agent_type": "error"
            }

    async def process_input(self, input_text: str, chain_id: Optional[int] = None, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process input text and route to the appropriate agent.
        Renamed from the original process method to avoid conflicts.
        """
        logger.info(f"Processing input: {input_text}")

        # Normalize input text
        normalized_text = input_text.lower().strip()
        
        # Handle yes/no confirmation responses first to avoid treating them as new commands
        if normalized_text in ["yes", "y", "yeah", "yep", "ok", "okay", "sure", "confirm"]:
            return {
                "content": {
                    "type": "confirmation",
                    "message": "Confirmed. Processing your request...",
                    "confirmed": True
                },
                "agent_type": "confirmation"
            }
        
        if normalized_text in ["no", "n", "nope", "cancel", "abort"]:
            return {
                "content": {
                    "type": "confirmation",
                    "message": "Cancelled. Let me know if you need anything else.",
                    "confirmed": False
                },
                "agent_type": "confirmation"
            }

        # Check for greetings first to avoid unnecessary agent initialization
        greetings = ["gm", "good morning", "hello", "hi", "hey", "howdy", "sup", "yo"]
        if any(greeting == normalized_text for greeting in greetings):
            return {
                "content": {
                    "type": "message",
                    "message": self._get_greeting_response()
                },
                "agent_type": "general"
            }

        # Check for help command
        if normalized_text == "help" or normalized_text == "what can you do" or normalized_text == "what can you do?" or "capabilities" in normalized_text:
            return {
                "content": {
                    "type": "message",
                    "message": self._get_help_response()
                },
                "agent_type": "general"
            }

        # Special case for the common "bridge $X of TOKEN to CHAIN" pattern that's failing in logs
        if normalized_text.startswith("bridge $") and " to " in normalized_text:
            logger.info(f"Detected special bridge pattern that needs Brian agent: {normalized_text}")
            try:
                brian_agent = self._get_brian_agent()
                # Convert chain_id string to int if provided
                chain_id_int = int(chain_id) if chain_id else None
                
                result = await brian_agent.process_brian_command(
                    command=input_text,
                    chain_id=chain_id_int,
                    wallet_address=wallet_address
                )
                if not result.get("error"):
                    # Successfully processed as Brian API command
                    result["agent_type"] = "brian"
                    return result
                else:
                    logger.warning(f"Brian API processing failed for special bridge pattern: {result.get('error')}")
                    return {
                        "content": {
                            "type": "message",
                            "message": f"I couldn't process your bridge command. Make sure it's in the format 'bridge $[amount] of [token] to [destination]' or 'bridge [amount] [token] to [destination]'."
                        },
                        "agent_type": "brian",
                        "error": result.get("error")
                    }
            except Exception as e:
                logger.error(f"Error processing special bridge pattern: {e}", exc_info=True)
                return {
                    "content": {
                        "type": "message",
                        "message": f"There was an error processing your bridge command: {str(e)}"
                    },
                    "agent_type": "brian",
                    "error": str(e)
                }
            
        # Check if this is a Brian API command (transfer, bridge, or balance)
        is_transfer_command = re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", normalized_text, re.IGNORECASE) is not None
        
        is_balance_command = re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", normalized_text, re.IGNORECASE) is not None
        
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
            ("what is" in normalized_text and any(token in normalized_text for token in ["eth", "btc", "usdc", "dai", "usdt", "bitcoin", "ethereum", "token", "coin", "crypto"])) or
            re.search(r"what\s+is\s+(?:the\s+)?price\s+of\s+([a-zA-Z0-9]+)", normalized_text) is not None
        )

        # Try to process as a Brian API command first
        if is_transfer_command or is_balance_command:
            try:
                logger.info(f"Processing as Brian API command: {input_text} (is_transfer_command: {is_transfer_command}, is_balance_command: {is_balance_command})")
                brian_agent = self._get_brian_agent()
                
                result = await brian_agent.process_brian_command(
                    command=input_text,
                    chain_id=chain_id_int,
                    wallet_address=wallet_address
                )
                if not result.get("error"):
                    # Successfully processed as Brian API command
                    result["agent_type"] = "brian"
                    return result
                else:
                    logger.warning(f"Brian API processing failed: {result.get('error')}")
                    # Return error with improved message rather than falling through
                    if is_transfer_command:
                        return {
                            "content": {
                                "type": "message",
                                "message": f"I couldn't process your transfer command. Make sure it's in the format 'send/transfer [amount] [token] to [recipient]'."
                            },
                            "agent_type": "brian",
                            "error": result.get("error")
                        }
                    elif is_balance_command:
                        return {
                            "content": {
                                "type": "message",
                                "message": f"I couldn't check your balance. Make sure you're connected to a wallet."
                            },
                            "agent_type": "brian",
                            "error": result.get("error")
                        }
            except Exception as e:
                logger.error(f"Error processing Brian API command: {e}", exc_info=True)
                # Return error with helpful message rather than falling through
                if is_transfer_command:
                    return {
                        "content": {
                            "type": "message",
                            "message": f"There was an error processing your command: {str(e)}"
                        },
                        "agent_type": "brian",
                        "error": str(e)
                    }
                elif is_balance_command:
                    return {
                        "content": {
                            "type": "message",
                            "message": f"There was an error checking your balance: {str(e)}"
                        },
                        "agent_type": "brian",
                        "error": str(e)
                    }

        # Try to process as a DCA command first
        if is_dca_command:
            try:
                logger.info("Processing as DCA command")
                dca_agent = self._get_dca_agent()
                result = await dca_agent.process_dca_command(
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
                swap_agent = self._get_swap_agent()
                result = await swap_agent.process_swap_command(input_text, chain_id)
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
                    elif "content" in result and "price" in result["content"]:
                        price_data = result["content"]
                        result["content"] = {
                            "type": "message",
                            "message": f"The current price of {price_data['token']['symbol']} is ${price_data['price']:.2f}."
                        }
                    result["agent_type"] = "price"
                    return result
                else:
                    logger.warning(f"Price query processing failed: {result.get('error')}")

                    # Fallback to direct token lookup if PriceAgent failed
                    token_match = re.search(r'\b(eth|btc|usdc|dai|usdt|bitcoin|ethereum)\b', normalized_text, re.IGNORECASE)
                    token = token_match.group(1).upper() if token_match else None

                    if token:
                        # If we have a token, try to get its price directly
                        try:
                            price, timestamp = await self.token_service.get_token_price(token, "usd", chain_id or 1)
                            if price is not None:
                                price_messages = [
                                    f"The current price of {token} is ${price:.2f}. Not that I care much, but thought you'd want to know.",
                                    f"Looks like {token} is worth ${price:.2f} right now. Do with that what you will.",
                                    f"${price:.2f} per {token}. That's what the internet tells me, anyway.",
                                    f"{token} is trading at ${price:.2f}. Buy high, sell low, right?",
                                    f"I checked, and {token} is going for ${price:.2f}. Not financial advice, obviously.",
                                    f"The price of {token} is ${price:.2f}. But prices are just, like, numbers, man.",
                                    f"{token}: ${price:.2f}. Do you want me to pretend to be excited about that?",
                                    f"I dragged myself all the way to the price API, and {token} is at ${price:.2f}.",
                                    f"${price:.2f} per {token}. I'm sure that means something to someone.",
                                    f"After extensive research (one API call), I can tell you that {token} is worth ${price:.2f}."
                                ]
                                return {
                                    "content": {
                                        "type": "message",
                                        "message": random.choice(price_messages)
                                    },
                                    "agent_type": "price"
                                }
                        except Exception as e:
                            logger.error(f"Error getting price directly: {e}")

                # If all methods failed, return a fallback response
                return {
                    "content": {
                        "type": "message",
                        "message": f"I tried to find the price for you, but I'm having trouble with the price service right now. Try again later?"
                    },
                    "agent_type": "price"
                }
            except Exception as e:
                logger.error(f"Error processing price query: {str(e)}")
                # Continue to general query processing

        # Process as a general query
        logger.info("Processing as general query")

        # Check one more time if this might be a price query that wasn't caught by our regex
        if re.search(r"(?:what|how much).*(?:price|worth|cost).*(?:of|is|for)\s+([a-zA-Z0-9]+)", normalized_text):
            logger.info("Detected possible price query in general handler, redirecting")
            try:
                price_agent = self.price_agent
                result = await price_agent.process_price_query(input_text, chain_id)
                if not result.get("error"):
                    result["content"]["type"] = "message"
                    result["agent_type"] = "price"
                    return result
            except Exception as e:
                logger.error(f"Error processing detected price query: {e}")
                # Continue to general processing

        # Extract token name if present
        token_match = re.search(r'\b(eth|btc|usdc|dai|usdt|bitcoin|ethereum)\b', normalized_text)
        token_name = token_match.group(1) if token_match else None

        if token_name and ("what" in normalized_text or "tell me about" in normalized_text):
            response = {
                "content": {
                    "type": "message",
                    "message": f"Looks like you're asking about {token_name.upper()}! If you want to know its price, try asking 'price {token_name}' or 'what is the price of {token_name}'."
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
            "gm, fren. More pointless financial decisions eh? why not!",  
            "Hey there! I'm feeling particularly lazy today, but I'll try to help.",
            "Oh hi! You caught me in the middle of my nap.",
            "Sup! I'm your friendly neighborhood pointless agent. What's on your mind?",
            "Hello! I'm here to pretend I know what I'm doing with your crypto.",
            "Hey hey hey! Another day, another opportunity to lose money together!",
            "Greetings, human! I'm here as I didn't have much else to do.",
            "Ah yes, another day pretending we understand life & blockchains, whats up?",
            "Ah, the sweet, futile waltz of existence. Lets dive in, the water's warm.",
            "Hello! How deliciously pointless, what up ... the weather?"
        ]
        return random.choice(greetings)
    
    def _get_help_response(self) -> str:
        """Get a help response with personality."""
        return (
            "What can SNEL do?\n\n"
            "Token Transfers\n"
            "\"send 10 USDC to 0x123...\"\n"
            "\"transfer 0.1 ETH to papajams.eth\"\n\n"
            "Cross-Chain Bridging\n"
            "\"bridge 0.1 ETH from Scroll to Base\"\n"
            "\"bridge 50 USDC from Ethereum to Arbitrum\"\n\n"
            "Balance Checking\n"
            "\"check my USDC balance on Scroll\"\n"
            "\"what's my ETH balance\"\n\n"
            "Token Swaps\n"
            "\"swap 1 ETH for USDC\"\n"
            "\"swap $100 worth of USDC for ETH\"\n\n"
            "DCA Orders\n"
            "\"** coming soon **\"\n"
            "\"** coming soon **\""
        )
    
    def _get_random_response(self, input_text: str) -> str:
        """Get a random response with personality."""
        responses = [
            f"I heard you say '{input_text}', but I'm too lazy to figure out what that means. Try asking for a price, token transfers, bridging, swaps, or DCA?",
            "That's cool and all, but have you tried asking me something I actually know about? Like token prices or swaps?",
            "Hmm, not sure what to do with that. I'm pretty pointless, but I can help with prices, token transfers, bridging, swaps, and DCA orders!",
            "I'd love to help, but that's outside my very limited skill set. Try asking about crypto prices, token transfers, bridging, swaps, or DCA orders instead?",
            f"'{input_text}'? That's nice, but I'm more into token swaps and price checks. Want to try one of those?",
            "I'm just a pointless agent pretending to be useful. Maybe try asking for a token price, token transfers, bridging, swaps, or DCA orders?",
            "I'm feeling particularly lazy today. Can you ask me something easier, like a token price, token transfers, bridging, swaps, or DCA orders?",
            "That's beyond my pointless existence. But I can check prices, token transfers, bridging, swaps, or DCA orders!",
            "I'm not smart enough for that. But I can pretend to be smart about crypto prices, token transfers, bridging, swaps, or DCA orders!",
            "I'm just a simple crypto agent with simple needs. Ask me about prices, token transfers, bridging, swaps, or DCA orders instead."
        ]
        return random.choice(responses)

    async def _process_dict_command(
        self, 
        command: Dict[str, Any], 
        wallet_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        user_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a command that came as a dictionary."""
        logger.info(f"Processing dict command: {command}")
        
        # Try to route to the appropriate agent based on any type indicators in the dict
        if command.get("is_brian_operation", False):
            logger.info("Routing to Brian agent based on is_brian_operation flag")
            return await self._process_with_brian_agent(command, wallet_address, chain_id, user_name)
        
        # Add more routing based on dict fields as needed
        
        # Default to general command processing
        return await self._process_general_query(str(command), wallet_address, chain_id, user_name, settings)
