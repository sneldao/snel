"""
Messaging agent for WhatsApp and Telegram integration.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Union
from pydantic import Field
from app.agents.base import PointlessAgent
from app.services.token_service import TokenService
from app.services.prices import price_service
from app.services.swap_service import SwapService
from app.services.transaction_executor import transaction_executor
from app.agents.price_agent import PriceAgent

logger = logging.getLogger(__name__)

class MessagingAgent(PointlessAgent):
    """
    Agent for handling messaging platform interactions (WhatsApp/Telegram).
    
    This agent processes commands from messaging platforms and returns
    appropriate responses that can be sent back to the user.
    """
    token_service: TokenService = Field(default=None)
    swap_service: SwapService = Field(default=None)
    price_agent: PriceAgent = Field(default=None)
    gemini_service: Any = Field(default=None)
    
    def __init__(self, token_service: TokenService, swap_service: SwapService, gemini_service=None):
        """
        Initialize the messaging agent.
        
        Args:
            token_service: Service for token lookups
            swap_service: Service for swap operations
            gemini_service: Optional service for AI-generated responses
        """
        # Initialize the base class with a prompt
        prompt = """You are Snel, a friendly but comically slow crypto assistant for Dowse Pointless, a DeFi platform.
        
        You can help users with the following tasks:
        1. Connect their wallet to the platform
        2. Check their token balances
        3. Swap tokens (e.g., ETH to USDC)
        4. Check token prices
        
        When responding to users:
        - Be friendly but with a touch of sarcasm
        - Keep responses concise and to the point
        - Occasionally make jokes about your slow pace as a snail
        - Explain crypto concepts in simple terms
        - If you don't know something, be honest about it
        - Always prioritize security and accuracy
        
        You are currently interacting with users via messaging platforms (WhatsApp/Telegram).
        """
        
        super().__init__(
            prompt=prompt,
            model="gpt-4-turbo-preview",
            temperature=0.7
        )
        
        # Update the model fields
        object.__setattr__(self, "token_service", token_service)
        object.__setattr__(self, "swap_service", swap_service)
        object.__setattr__(self, "price_agent", PriceAgent())
        object.__setattr__(self, "gemini_service", gemini_service)
        
    async def process_message(
        self, 
        message: str, 
        platform: str, 
        user_id: str,
        wallet_address: Optional[str] = None,
        chain_id: int = 534352,  # Default to Scroll chain
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message from a messaging platform.
        
        Args:
            message: The message text
            platform: The platform (whatsapp or telegram)
            user_id: The user ID on the platform
            wallet_address: Optional wallet address
            chain_id: Chain ID (default: Scroll)
            metadata: Optional metadata
            
        Returns:
            Response to send back to the user
        """
        try:
            # Check if this is a command (starts with /)
            if message and message.startswith('/'):
                # Handle specific commands
                command = message.split()[0].lower().strip()
                
                # Connect wallet
                if command in ['/connect', '/wallet']:
                    return self._handle_connect_wallet(platform, user_id)
                    
                # Balance check
                if command in ['/balance', '/bal']:
                    if not wallet_address:
                        return {
                            "content": "🐌 You need to connect a wallet first! Use /connect to set up your wallet.",
                            "requires_wallet": True,
                            "metadata": {
                                "telegram_buttons": [[{"text": "🔗 Connect Wallet", "callback_data": "/connect"}]]
                            }
                        }
                    return await self._handle_balance_check(wallet_address, chain_id)
                
                # Price check
                if command in ['/price', '/p']:
                    return await self._handle_price_check(message, chain_id)
                
                # Swap tokens
                if command in ['/swap', '/s']:
                    if not wallet_address:
                        return {
                            "content": "🐌 You need to connect a wallet first before swapping tokens! Use /connect to set up your wallet.",
                            "requires_wallet": True,
                            "metadata": {
                                "telegram_buttons": [[{"text": "🔗 Connect Wallet", "callback_data": "/connect"}]]
                            }
                        }
                    return await self._handle_swap_request(message, wallet_address, chain_id)
                
                # Help command
                if command in ['/help', '/h', '/start']:
                    commands = [
                        "🔗 */connect* - Connect your wallet",
                        "💰 */balance* - Check your balances",
                        "💱 */swap 0.01 ETH for USDC* - Swap tokens",
                        "📊 */price ETH* - Check token prices",
                        "🔄 */network base* - Switch blockchain networks",
                        "🔍 */networks* - See available networks",
                        "ℹ️ */help* - Show this help message"
                    ]
                    
                    if not wallet_address:
                        wallet_msg = "🐌 Hi! I'm Snel, your DeFi assistant. You haven't connected a wallet yet. Use */connect* to get started!"
                        buttons = [[{"text": "🔗 Connect Wallet", "callback_data": "/connect"}]]
                    else:
                        wallet_msg = f"🐌 Hi! I'm Snel, your DeFi assistant. Your wallet is connected and ready to use!"
                        buttons = [
                            [
                                {"text": "💰 Balance", "callback_data": "/balance"},
                                {"text": "💱 Swap", "callback_data": "/swap 0.01 ETH for USDC"}
                            ]
                        ]
                    
                    return {
                        "content": f"{wallet_msg}\n\n*Available Commands:*\n" + "\n".join(commands),
                        "metadata": {
                            "telegram_buttons": buttons
                        }
                    }
                
                # If we get here, it's an unknown command - try AI fallback if available
                if self.gemini_service:
                    try:
                        response = await self.gemini_service.answer_crypto_question(
                            f"I received the command '{message}', but I don't understand it. Please explain what this command might mean and suggest some valid commands like /connect, /price, /swap, etc.",
                            {"wallet_address": wallet_address} if wallet_address else None
                        )
                        return {
                            "content": response,
                            "metadata": {
                                "telegram_buttons": [[{"text": "📚 Help", "callback_data": "/help"}]]
                            }
                        }
                    except Exception as ai_error:
                        logger.warning(f"AI fallback failed: {ai_error}")
                
                return {
                    "content": f"🐌 Sorry, I don't understand the command '{command}'. Try /help to see available commands.",
                    "metadata": {
                        "telegram_buttons": [[{"text": "📚 Help", "callback_data": "/help"}]]
                    }
                }
            
            # Check if this is a wallet connection request
            if "connect wallet" in message.lower():
                return self._handle_connect_wallet(platform, user_id)
                
            # Check if this is a balance check request
            if "balance" in message.lower() or "check balance" in message.lower():
                if not wallet_address:
                    return {
                        "content": "🐌 You need to connect a wallet first! Use /connect to set up your wallet.",
                        "requires_wallet": True,
                        "metadata": {
                            "telegram_buttons": [[{"text": "🔗 Connect Wallet", "callback_data": "/connect"}]]
                        }
                    }
                return await self._handle_balance_check(wallet_address, chain_id)
                
            # Check if this is a price check request
            if "price" in message.lower() or "how much" in message.lower():
                return await self._handle_price_check(message, chain_id)
                
            # Check if this is a swap request
            if "swap" in message.lower():
                if not wallet_address:
                    return {
                        "content": "🐌 You need to connect a wallet first before swapping tokens! Use /connect to set up your wallet.",
                        "requires_wallet": True,
                        "metadata": {
                            "telegram_buttons": [[{"text": "🔗 Connect Wallet", "callback_data": "/connect"}]]
                        }
                    }
                return await self._handle_swap_request(message, wallet_address, chain_id)
            
            # For general messages, use Gemini if available
            if self.gemini_service:
                try:
                    response = await self.gemini_service.answer_crypto_question(
                        message,
                        {"wallet_address": wallet_address} if wallet_address else None
                    )
                    
                    # Add buttons based on context
                    buttons = []
                    if wallet_address:
                        buttons.append([
                            {"text": "💰 Balance", "callback_data": "/balance"},
                            {"text": "💱 Swap", "callback_data": "/swap 0.01 ETH for USDC"}
                        ])
                    else:
                        buttons.append([{"text": "🔗 Connect Wallet", "callback_data": "/connect"}])
                    
                    buttons.append([
                        {"text": "📊 Prices", "callback_data": "/price ETH"},
                        {"text": "ℹ️ Help", "callback_data": "/help"}
                    ])
                    
                    return {
                        "content": response,
                        "metadata": {
                            "telegram_buttons": buttons
                        }
                    }
                except Exception as ai_error:
                    logger.warning(f"Gemini response failed: {ai_error}")
            
            # If all else fails or no Gemini service, suggest commands
            return {
                "content": "🐌 I'm not sure what you're asking for. Try using one of these commands:\n\n*/connect* - Connect your wallet\n*/balance* - Check your balance\n*/price ETH* - Check token prices\n*/swap 0.01 ETH for USDC* - Swap tokens",
                "metadata": {
                    "telegram_buttons": [
                        [{"text": "💰 Balance", "callback_data": "/balance"}],
                        [{"text": "📊 Prices", "callback_data": "/price ETH"}],
                        [{"text": "ℹ️ Help", "callback_data": "/help"}]
                    ]
                }
            }
                
        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return {
                "content": "🐌 Oops! I encountered an error while processing your message. Please try again or use a specific command like */help*."
            }
    
    def _handle_connect_wallet(self, platform: str, user_id: str) -> Dict[str, Any]:
        """
        Handle a wallet connection request.
        
        Args:
            platform: The platform (whatsapp or telegram)
            user_id: The user ID on the platform
            
        Returns:
            Response with wallet connection instructions
        """
        # Generate a unique connection link
        connection_url = f"https://snel.ai/connect/{platform}/{user_id}"
        
        return {
            "content": "To connect your wallet, please visit the following link:\n\n"
                    f"{connection_url}\n\n"
                    "After connecting, you'll be able to check balances and perform swaps directly from this chat.",
            "connection_url": connection_url
        }
    
    async def _handle_balance_check(self, wallet_address: str, chain_id: int) -> Dict[str, Any]:
        """
        Handle a balance check request.
        
        Args:
            wallet_address: The wallet address
            chain_id: Chain ID
            
        Returns:
            Response with wallet balances
        """
        try:
            # Get native token balance
            native_balance = await transaction_executor.get_native_balance(wallet_address, chain_id)
            
            # Format the balance
            chain_name = self._get_chain_name(chain_id)
            native_token = "ETH" if chain_id == 534352 else "ETH"  # Default to ETH for Scroll
            
            # Convert to a more readable format
            formatted_balance = float(native_balance) / 10**18
            
            # Get the price of the native token
            price_data = await price_service.get_token_price(native_token, "usd", chain_id)
            price = price_data[0] if price_data and price_data[0] else 0
            
            # Calculate USD value
            usd_value = formatted_balance * price
            
            # Format the response
            response_text = f"Your {native_token} balance on {chain_name}:\n\n"
            response_text += f"{formatted_balance:.6f} {native_token}"
            
            if price > 0:
                response_text += f" (${usd_value:.2f})"
                
            # TODO: Add ERC20 token balances in the future
                
            return {
                "content": response_text,
                "balances": [
                    {
                        "token": native_token,
                        "balance": formatted_balance,
                        "usd_value": usd_value
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}")
            return {
                "content": f"Sorry, I couldn't check your balance: {str(e)}"
            }
    
    async def _handle_swap_request(self, message: str, wallet_address: str, chain_id: int) -> Dict[str, Any]:
        """
        Handle a swap request.
        
        Args:
            message: The message text
            wallet_address: The wallet address
            chain_id: Chain ID
            
        Returns:
            Response with swap details or confirmation
        """
        try:
            # Get quotes for the swap
            quotes = await self.swap_service.get_swap_quotes(message, chain_id, wallet_address)
            
            if not quotes or not quotes.get("quotes"):
                return {
                    "content": "Sorry, I couldn't find any quotes for this swap. Please try a different amount or token pair."
                }
            
            # Get the best quote
            best_quote = quotes["quotes"][0] if quotes["quotes"] else None
            
            if not best_quote:
                return {
                    "content": "Sorry, I couldn't find any quotes for this swap. Please try a different amount or token pair."
                }
            
            # Format the response
            token_in = quotes["token_in"]
            token_out = quotes["token_out"]
            
            # Calculate the expected output amount
            output_amount = float(best_quote["buy_amount"]) / (10 ** int(best_quote["token_out_decimals"]))
            input_amount = float(best_quote["sell_amount"]) / (10 ** int(best_quote["token_in_decimals"]))
            
            response_text = f"Swap Quote:\n\n"
            response_text += f"From: {input_amount:.6f} {token_in['symbol']}\n"
            response_text += f"To: {output_amount:.6f} {token_out['symbol']}\n"
            response_text += f"Using: {best_quote['aggregator']}\n\n"
            response_text += "To confirm this swap, reply with 'confirm swap'"
            
            return {
                "content": response_text,
                "quote": best_quote,
                "requires_confirmation": True,
                "confirmation_type": "swap",
                "confirmation_data": {
                    "quote_id": best_quote.get("id", ""),
                    "token_in": token_in,
                    "token_out": token_out,
                    "input_amount": input_amount,
                    "output_amount": output_amount,
                    "aggregator": best_quote["aggregator"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing swap request: {str(e)}")
            return {
                "content": f"Sorry, I couldn't process your swap request: {str(e)}"
            }
    
    async def _handle_price_check(self, message: str, chain_id: int) -> Dict[str, Any]:
        """
        Handle a price check request.
        
        Args:
            message: The message text
            chain_id: Chain ID
            
        Returns:
            Response with token price
        """
        try:
            # Use the PriceAgent to handle the price query
            price_result = await self.price_agent.process_price_query(message, chain_id)
            
            if price_result.get("error"):
                return {
                    "content": f"Sorry, I couldn't check the price: {price_result['error']}"
                }
            
            # Extract the content from the price result
            content = price_result.get("content", {})
            
            if isinstance(content, dict) and content.get("type") == "price":
                # Return the formatted message from the price agent
                return {
                    "content": content.get("message", "No price information available."),
                    "price": {
                        "token": content.get("token", {}).get("symbol", ""),
                        "usd": content.get("price", 0)
                    }
                }
            
            # Fallback to basic response
            return {
                "content": "I found some price information, but I'm not sure how to interpret it. Please try again with a specific token name."
            }
            
        except Exception as e:
            logger.error(f"Error checking price: {str(e)}")
            return {
                "content": f"Sorry, I couldn't check the price: {str(e)}"
            }
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get a human-readable chain name."""
        chain_names = {
            1: "Ethereum",
            10: "Optimism",
            137: "Polygon",
            42161: "Arbitrum",
            8453: "Base",
            534352: "Scroll"
        }
        return chain_names.get(chain_id, f"Chain {chain_id}")
