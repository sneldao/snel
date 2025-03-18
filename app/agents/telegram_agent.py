"""
Telegram-specific agent for handling Telegram bot interactions.
"""
import logging
import json
import re
import random
import hashlib
import time
import os
from typing import Dict, Any, List, Optional, Union, Tuple, Callable, Type
from pydantic import Field
from app.agents.messaging_agent import MessagingAgent
from app.services.prices import PriceService
from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.wallet_service import WalletService
from app.services.smart_wallet_service import SmartWalletService
from app.services.gemini_service import GeminiService
from app.models.telegram import TelegramWebhookRequest

logger = logging.getLogger(__name__)

# Default blockchain network
DEFAULT_CHAIN = "base_sepolia"

class TelegramAgent(MessagingAgent):
    """
    Agent for handling Telegram-specific interactions.
    
    This agent extends the MessagingAgent with Telegram-specific features
    like commands, wallet creation, and inline buttons.
    """
    command_handlers: Dict[str, Callable] = Field(default_factory=dict)
    wallet_service: Optional[SmartWalletService] = None
    gemini_service: Optional[GeminiService] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(
        self, 
        token_service: TokenService, 
        swap_service: SwapService,
        wallet_service: Optional[SmartWalletService] = None,
        gemini_service: Optional[GeminiService] = None
    ):
        """
        Initialize the Telegram agent.
        
        Args:
            token_service: Service for managing tokens and chains
            swap_service: Service for swap-related operations
            wallet_service: Optional wallet service for wallet operations
            gemini_service: Optional Gemini service for AI-powered responses
        """
        super().__init__(token_service, swap_service)
        
        # Initialize SmartWalletService if not provided
        if wallet_service is None:
            redis_url = os.getenv("REDIS_URL")
            self.wallet_service = SmartWalletService(redis_url=redis_url)
        else:
            self.wallet_service = wallet_service
            
        self.gemini_service = gemini_service
        
        # Register command handlers
        self.command_handlers = {
            "start": self._handle_start_command,
            "help": self._handle_help_command,
            "connect": self._handle_connect_command,
            "balance": self._handle_balance_command,
            "price": self._handle_price_command,
            "swap": self._handle_swap_command,
            "disconnect": self._handle_disconnect_command,
            "networks": self._handle_networks_command,
            "network": self._handle_network_command,
            "keys": self._handle_keys_command,
            "faucet": self._handle_faucet_command,
            "test": self._handle_test_command
        }
        
        logger.info("TelegramAgent initialized with commands: %s", list(self.command_handlers.keys()))

    async def process_telegram_update(
        self,
        update: Dict[str, Any],
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a Telegram update object.
        
        Args:
            update: Telegram update object
            user_id: Telegram user ID
            wallet_address: User's wallet address if already connected
            metadata: Additional metadata
            
        Returns:
            Dict with response content and any additional information
        """
        logger.info(f"Processing Telegram update for user {user_id}")
        logger.info(f"Update content: {json.dumps(update, indent=2)}")
        
        # Handle different types of updates
        if "message" in update and "text" in update["message"]:
            message_text = update["message"]["text"]
            logger.info(f"Processing text message: '{message_text}'")
            return await self._process_telegram_message(message_text, user_id, wallet_address, metadata)
        elif "callback_query" in update:
            # Handle button callbacks
            callback_data = update["callback_query"]["data"]
            logger.info(f"Processing callback query: '{callback_data}'")
            return await self._process_callback_query(user_id, callback_data, wallet_address)
        else:
            # Default response for unsupported update types
            logger.warning(f"Unsupported update type: {list(update.keys())}")
            return {
                "content": "Sorry, I can only handle text messages and button clicks for now.",
                "metadata": {"telegram_buttons": None}
            }

    async def _process_telegram_message(
        self,
        message: str,
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a text message from Telegram.
        
        Args:
            message: Message text
            user_id: Telegram user ID
            wallet_address: User's wallet address if already connected
            metadata: Additional metadata
            
        Returns:
            Dict with response content and any additional information
        """
        # Check if this is a command
        if message.startswith("/"):
            command_parts = message.split(" ", 1)
            
            # Remove the leading slash and split at @
            command = command_parts[0].lstrip("/").split("@")[0].lower()
            
            args = command_parts[1] if len(command_parts) > 1 else ""
            
            logger.info(f"Processing command: {command} with args: {args}")
            
            # Dispatch to the appropriate command handler
            if command in self.command_handlers:
                handler = self.command_handlers[command]
                response = await handler(user_id, args, wallet_address)
                
                # Add personality to the response
                if "content" in response:
                    response["content"] = self._add_telegram_personality(response["content"])
                    
                return response
            else:
                logger.warning(f"Unknown command received: {command}")
                return {
                    "content": "I don't recognize that command. Try /help to see what I can do."
                }
        
        # If not a command, process as a regular message
        result = await self.process_message(
            message=message,
            platform="telegram",
            user_id=user_id,
            wallet_address=wallet_address,
            metadata=metadata
        )
        
        # Add Telegram-specific personality
        result["content"] = self._add_telegram_personality(result["content"])
        
        return result

    async def _process_callback_query(
        self,
        user_id: str,
        callback_data: str,
        wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a callback query from an inline button.
        
        Args:
            user_id: Telegram user ID
            callback_data: Data from the callback query
            wallet_address: User's wallet address
            
        Returns:
            Dict with response content
        """
        logger.info(f"Processing callback query: {callback_data}")
        
        # Handle different callback queries
        if callback_data == "connect_wallet":
            return await self._handle_connect_command(user_id, "", wallet_address)
        
        elif callback_data == "check_balance":
            return await self._handle_balance_command(user_id, "", wallet_address)
        
        elif callback_data == "show_help":
            return await self._handle_help_command(user_id, "", wallet_address)
        
        elif callback_data == "show_networks":
            return await self._handle_networks_command(user_id, "", wallet_address)
        
        elif callback_data == "create_new_wallet":
            return await self._handle_connect_command(user_id, "new", wallet_address)
        
        elif callback_data == "get_faucet":
            return await self._handle_faucet_command(user_id, "", wallet_address)
        
        elif callback_data == "show_address":
            try:
                # Get wallet data from smart wallet service
                wallet_data = await self.wallet_service.get_smart_wallet(user_id, platform="telegram")
                
                if wallet_data and wallet_data.get("address"):
                    address = wallet_data.get("address")
                    return {
                        "content": f"Your wallet address is:\n\n`{address}`\n\nYou can copy this address to receive funds.",
                        "parse_mode": "Markdown"
                    }
                else:
                    return {
                        "content": "You don't have a wallet connected yet. Use /connect to create one."
                    }
            except Exception as e:
                logger.error(f"Error showing address: {e}")
                return {
                    "content": "There was an error retrieving your wallet address. Please try again later."
                }
        
        elif callback_data.startswith("network:"):
            network = callback_data.split(":", 1)[1]
            return await self._handle_network_command(user_id, network, wallet_address)
            
        elif callback_data.startswith("select_network:"):
            network = callback_data.split(":", 1)[1]
            logger.info(f"Switching to network {network} for user {user_id}")
            return await self._handle_network_command(user_id, network, wallet_address)
        
        elif callback_data.startswith("swap_approve:"):
            swap_id = callback_data.split(":", 1)[1]
            return await self._approve_swap(user_id, swap_id, wallet_address)
        
        elif callback_data.startswith("swap_cancel:"):
            swap_id = callback_data.split(":", 1)[1]
            return await self._cancel_swap(user_id, swap_id, wallet_address)
        
        elif callback_data == "suggest_help":
            return {
                "content": "Here are some things you can ask me about:\n\n" +
                          "• Cryptocurrency prices\n" +
                          "• How to set up a wallet\n" +
                          "• What are smart contracts\n" +
                          "• Differences between blockchains\n" +
                          "• What is Base/Scroll\n\n" +
                          "You can also use /help to see available commands."
            }
            
        elif callback_data == "suggest_swap" or callback_data == "create_wallet":
            return await self._handle_connect_command(user_id, "", wallet_address)
            
        elif callback_data.startswith("suggest_swap_"):
            # Format: suggest_swap_TOKEN
            token = callback_data.split("_")[-1]
            return {
                "content": f"To swap {token}, use the command format:\n\n" +
                          f"/swap [amount] {token} for [token]\n\n" +
                          f"Example: /swap 0.1 {token} for USDC"
            }
        
        # Default response
        return {
            "content": "I'm not sure how to handle that request. Try using /help to see available commands."
        }

    def _add_telegram_personality(self, content: str) -> str:
        """
        Add personality to Telegram responses.
        
        Args:
            content: Original response content
            
        Returns:
            Enhanced content with personality
        """
        if not content:
            return content

        # Define snail emojis to add personality
        snail_emojis = ["🐌", "🐌 ", "🐌💨", "🐢"]

        # Define quips about being slow but reliable
        slow_quips = [
            "(Sorry for the delay, moving as fast as my shell allows!)",
            "(Zooming at snail speed...)",
            "(I might be slow, but I'll get you there safely!)",
            "(Taking my time to get things right! 🐌)",
            "(Slow and steady wins the DeFi race!)",
            "(Every transaction is a marathon, not a sprint!)",
            "(Quality over speed, that's the snail way!)"
        ]

        # Get a random emoji and quip
        emoji = random.choice(snail_emojis) if random.random() < 0.4 else ""
        quip = random.choice(slow_quips) if random.random() < 0.25 and len(content) > 50 else ""

        # Avoid adding emoji to error messages
        if "error" in content.lower() or "sorry" in content.lower():
            emoji = ""
            quip = ""

        # Format the content with emoji and quip
        result = content

        # Add emoji if not already at the beginning
        if emoji and not content.startswith("🐌") and not content.startswith("🐢"):
            # Add emoji at a logical position, not breaking markdown or between words
            if "\n" in content[:20]:
                # Add after the first line
                first_newline = content.find("\n")
                result = content[:first_newline+1] + emoji + " " + content[first_newline+1:]
            else:
                # Add at the beginning
                result = f"{emoji} {content}"

        # Add quip to the end
        if quip and not content.endswith(")"):
            result += f"\n\n{quip}"

        # Enhance command visibility by adding asterisks around commands
        command_pattern = r'(/[a-z_]+)'
        result = re.sub(command_pattern, r'*\1*', result)

        return result

    async def _handle_start_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /start command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        # Create buttons for getting started
        buttons = []

        # If user already has a wallet, show wallet options
        if wallet_address:
            buttons.extend(
                (
                    [
                        {
                            "text": "💰 Check Balance",
                            "callback_data": "check_balance",
                        },
                        {
                            "text": "🌐 Switch Network",
                            "callback_data": "show_networks",
                        },
                    ],
                    [
                        {
                            "text": "📊 Price Check",
                            "callback_data": "suggest_price",
                        },
                        {
                            "text": "🔄 Swap Tokens",
                            "callback_data": "suggest_swap",
                        },
                    ],
                )
            )
            return {
                "content": f"Welcome back to Snel DeFi Assistant! 🐌\n\n" +
                    f"Your wallet `{wallet_address[:6]}...{wallet_address[-4:]}` is connected.\n\n" +
                    f"What would you like to do today?",
                "metadata": {
                    "telegram_buttons": buttons
                }
            }

        # New user flow
        buttons.append([
            {"text": "💼 Create Wallet", "callback_data": "create_wallet"}
        ])
        buttons.append([
            {"text": "ℹ️ Learn More", "callback_data": "show_help"}
        ])

        return {
            "content": "Hello! I'm Snel, your friendly DeFi assistant! 🐌\n\n" +
                "I can help you navigate the world of decentralized finance with:\n\n" +
                "• Crypto wallet management\n" +
                "• Token swaps and transfers\n" +
                "• Price tracking and alerts\n" +
                "• Multi-chain support\n\n" +
                "Would you like to create a wallet to get started?",
            "metadata": {
                "telegram_buttons": buttons
            }
        }

    async def _handle_help_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /help command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        # Create buttons for common actions
        buttons = []

        # Add wallet-specific buttons if user has a wallet
        if wallet_address:
            buttons.append([
                {"text": "💰 Check Balance", "callback_data": "check_balance"},
                {"text": "🌐 Switch Network", "callback_data": "show_networks"}
            ])
        else:
            buttons.append([
                {"text": "💼 Create Wallet", "callback_data": "create_wallet"}
            ])

        # Add general help buttons
        buttons.append([
            {"text": "🔍 View Networks", "callback_data": "show_networks"},
            {"text": "🔐 Key Custody", "callback_data": "keys_help"}
        ])

        help_text = (
            "🐌 **Snel DeFi Assistant Commands:**\n\n" + "**Wallet Commands:**\n"
        )
        help_text += "• */connect* - Create or connect a wallet\n"
        help_text += "• */balance* - Check your wallet balance\n"
        help_text += "• */disconnect* - Disconnect your wallet\n"
        help_text += "• */keys* - Learn about key management\n\n"

        # Trading commands
        help_text += "**Trading Commands:**\n"
        help_text += "• */price ETH* - Check token prices\n"
        help_text += "• */swap 0.1 ETH for USDC* - Swap tokens\n\n"

        # Network commands
        help_text += "**Network Commands:**\n"
        help_text += "• */networks* - See available networks\n"
        help_text += "• */network base_sepolia* - Switch to a network\n\n"

        # Informational commands
        help_text += "**Other Commands:**\n"
        help_text += "• */help* - Show this help message\n\n"

        # Add info about general questions
        help_text += "You can also ask me general questions about DeFi, crypto, and blockchain technology!"

        return {
            "content": help_text,
            "metadata": {
                "telegram_buttons": buttons
            }
        }
    async def _handle_connect_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /connect command to connect or create a wallet.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content and optional button markup
        """
        try:
            # User wants to create a new wallet (even if they have an existing one)
            create_new = "new" in args.lower()

            # If the user already has a wallet and isn't creating a new one
            if wallet_address and not create_new:
                buttons = [
                    [
                        {"text": "💰 Check Balance", "callback_data": "check_balance"},
                        {"text": "🌐 Switch Networks", "callback_data": "show_networks"}
                    ],
                    [
                        {"text": "🔄 Create New Wallet", "callback_data": "create_new_wallet"}
                    ]
                ]

                return {
                    "content": f"You already have a wallet connected: `{wallet_address}`\n\n" +
                               "You can check your balance, switch networks, or create a new wallet if needed.",
                    "metadata": {
                        "telegram_buttons": buttons
                    }
                }

            # Create a new smart wallet
            logger.info(f"Creating new smart wallet for Telegram user {user_id}")

            # Verify we have the right wallet service type
            if not hasattr(self.wallet_service, 'create_smart_wallet'):
                logger.error("Wallet service doesn't have create_smart_wallet method. Type: " + 
                             str(type(self.wallet_service).__name__))
                return {
                    "content": "⚠️ Smart wallet creation is not available right now. Please try again later."
                }

            wallet_result = await self.wallet_service.create_smart_wallet(
                user_id=user_id, platform="telegram"
            )

            logger.info(f"Wallet creation result: {wallet_result}")

            # Check for success flag
            if not wallet_result.get("success", False):
                error_msg = wallet_result.get("error", "Unknown error")
                # Provide a friendly error message
                return {
                    "content": f"⚠️ I couldn't create a wallet right now. There was an issue with our wallet provider.\n\n" +
                               f"Error details: {error_msg}\n\n" +
                               "Please try again later or contact support."
                }

            # Get the wallet address
            new_wallet_address = wallet_result.get("address")

            # Return success response
            buttons = [
                [
                    {"text": "💰 Check Balance", "callback_data": "check_balance"},
                    {"text": "📝 View Address", "callback_data": "show_address"}
                ],
                [
                    {"text": "🚰 Get Test ETH", "callback_data": "get_faucet"}
                ]
            ]

            return {
                "content": f"✅ Your wallet has been created successfully!\n\n" +
                           f"Wallet Type: Coinbase CDP Smart Wallet\n" +
                           f"Network: Base Sepolia (testnet)\n\n" +
                           "Your wallet address is:\n" +
                           f"`{new_wallet_address}`\n\n" +
                           "You can now use this wallet to check prices, make swaps, and more.\n\n" +
                           "To get started, you'll need some testnet ETH. Click 'Get Test ETH' below.",
                "wallet_address": new_wallet_address,
                "metadata": {
                    "telegram_buttons": buttons
                }
            }

        except Exception as e:
            logger.exception(f"Error creating wallet: {e}")
            return {
                "content": "⚠️ Sorry, I encountered an error while creating your wallet. Please try again later."
            }
    async def _handle_balance_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /balance command to show wallet balance.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already known
            
        Returns:
            Dict with response content and buttons
        """
        try:
            # Log the command execution with more details
            logger.info(f"Processing balance command for user {user_id}")
            
            # Get wallet data
            wallet_data = await self.wallet_service.get_smart_wallet(user_id, platform="telegram")
            logger.info(f"Retrieved wallet data: {wallet_data}")
            
            if not wallet_data or not wallet_data.get("address"):
                return {
                    "content": "⚠️ You don't have a wallet yet. Please use /connect to create one."
                }
            
            wallet_address = wallet_data.get("address")
            wallet_chain = wallet_data.get("chain", "base_sepolia")
            
            logger.info(f"Getting balance for {wallet_address} on chain {wallet_chain}")
            
            # Get wallet balance
            try:
                balance_data = await self.wallet_service.get_wallet_balance(
                    user_id=user_id, 
                    platform="telegram", 
                    chain=wallet_chain
                )
                logger.info(f"Balance data: {balance_data}")
            except Exception as balance_error:
                logger.exception(f"Error getting wallet balance: {balance_error}")
                return {
                    "content": f"⚠️ There was an error retrieving your wallet balance: {str(balance_error)}\n\n" +
                              f"Wallet Address: `{wallet_address}`\n" +
                              f"Network: {wallet_chain.replace('_', ' ').title()}",
                    "parse_mode": "Markdown"
                }
            
            if not balance_data.get("success", False):
                error_msg = balance_data.get("error", "Unknown error")
                logger.error(f"Error getting balance for {user_id}: {error_msg}")
                
                return {
                    "content": f"⚠️ There was an error retrieving your wallet balance: {error_msg}\n\n" +
                              f"Wallet Address: `{wallet_address}`\n" +
                              f"Network: {wallet_chain.replace('_', ' ').title()}",
                    "parse_mode": "Markdown"
                }
            
            # Format the balance nicely
            eth_balance = balance_data.get("balance", "0")
            chain_info = balance_data.get("chain_info", {})
            network_name = chain_info.get("name", wallet_chain.replace("_", " ").title())
            is_testnet = chain_info.get("is_testnet", "sepolia" in wallet_chain)
            
            # Create buttons
            buttons = [
                [
                    {"text": "🔄 Refresh Balance", "callback_data": "check_balance"},
                    {"text": "📋 Show Address", "callback_data": "show_address"}
                ]
            ]
            
            # Add faucet button for testnet networks
            if is_testnet:
                buttons.append([
                    {"text": "🚰 Get Test ETH", "callback_data": "get_faucet"}
                ])
            
            # Create response message
            message = f"💰 **Wallet Balance**\n\n"
            message += f"**{eth_balance} ETH**\n\n"
            message += f"🔗 Network: {network_name}\n"
            message += f"📬 Address: `{wallet_address}`\n\n"
            
            if is_testnet:
                message += "_This is a testnet wallet. The tokens have no real value._\n\n"
                message += "Need testnet ETH? Click 'Get Test ETH' below."
            
            return {
                "content": message,
                "parse_mode": "Markdown",
                "buttons": buttons
            }
            
        except Exception as e:
            # Provide more detailed error information
            logger.exception(f"Error handling balance command: {e}")
            return {
                "content": f"❌ There was an error checking your balance: {str(e)}\n\nPlease try again later or contact support if the problem persists."
            }

    async def _handle_price_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /price command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments (token symbol)
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not args:
            return {
                "content": "Please specify a token symbol. Example: /price ETH"
            }
            
        # Extract token symbol
        token_symbol = args.strip().upper()
        
        try:
            # Try to get the price from the price service
            price_data = await PriceService.get_token_price(token_symbol)
            
            if not price_data or "error" in price_data:
                return {
                    "content": f"Sorry, I couldn't find price information for {token_symbol}. Try a popular token like ETH, BTC, USDC, or USDT."
                }
                
            price = price_data.get("price", 0)
            change_24h = price_data.get("change_24h", 0)
            
            # Format the price based on its value
            if price >= 100:
                price_str = f"${price:,.2f}"
            elif price >= 1:
                price_str = f"${price:.4f}"
            else:
                price_str = f"${price:.6f}"
                
            # Determine if the price went up or down
            if change_24h > 0:
                change_text = f"📈 +{change_24h:.2f}%"
            elif change_24h < 0:
                change_text = f"📉 {change_24h:.2f}%"
            else:
                change_text = "➡️ 0.00%"
                
            # Create buttons for common actions
            buttons = []
            buttons.append([
                {"text": f"Swap {token_symbol}", "callback_data": f"suggest_swap_{token_symbol}"},
                {"text": "Check Another", "callback_data": "suggest_price"}
            ])
            
            return {
                "content": f"💰 **{token_symbol} Price**\n\n" +
                    f"Current Price: {price_str}\n" +
                    f"24h Change: {change_text}\n\n" +
                    f"Last updated: {price_data.get('last_updated', 'just now')}\n\n" +
                    f"To check another token price, use */price [symbol]*\n" +
                    f"To swap tokens, use */swap [amount] [token] for [token]*",
                "metadata": {
                    "telegram_buttons": buttons
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting price for {token_symbol}: {e}")
            return {
                "content": f"Sorry, I encountered an error getting the price for {token_symbol}. Please try again later."
            }

    async def _handle_swap_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /swap command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content and optional button markup
        """
        logger.info(f"Processing swap command: '{args}' for user {user_id}")
        
        if not wallet_address:
            return {
                "content": "You need to connect a wallet first. Use /connect to set up your wallet."
            }
        
        if not args:
            return {
                "content": "Please specify the swap details. Example: /swap 0.1 ETH for USDC"
            }
        
        # Parse the swap text - be more flexible with the regex pattern
        swap_match = re.search(r"(\d+\.?\d*)\s+(\w+)(?:\s+(?:to|for)\s+)(\w+)", args, re.I)
        
        if not swap_match:
            return {
                "content": "I couldn't understand your swap request. Please use the format:\n" +
                    "/swap [amount] [token] for [token]\n\n" +
                    "Example: /swap 0.1 ETH for USDC"
            }
        
        amount, from_token, to_token = swap_match.groups()
        from_token = from_token.upper()
        to_token = to_token.upper()
        
        # Get the wallet's current chain
        try:
            wallet_data = await self.wallet_service.get_smart_wallet(user_id, platform="telegram")
            wallet_chain = wallet_data.get("chain", "base_sepolia")
            
            # For testnet networks, add a note about simulated swaps
            is_testnet = "sepolia" in wallet_chain or "goerli" in wallet_chain
            
            if is_testnet:
                # For testnet, simulate getting a quote
                # Use more realistic prices for common tokens
                price_map = {
                    "ETH": {"USDC": 1800, "USDT": 1795, "WETH": 0.995, "BTC": 0.06},
                    "USDC": {"ETH": 0.00055, "USDT": 0.998, "BTC": 0.000033},
                    "USDT": {"ETH": 0.00056, "USDC": 1.002, "BTC": 0.000033},
                    "BTC": {"ETH": 16.5, "USDC": 30000, "USDT": 29900}
                }
                
                # Apply a small random price variation
                base_rate = 0
                if from_token in price_map and to_token in price_map[from_token]:
                    base_rate = price_map[from_token][to_token]
                else:
                    # Default fallback for tokens not in our map
                    base_rate = 1.0  # 1:1 as fallback
                
                # Apply a small random variation (±5%)
                variation = random.uniform(0.95, 1.05)
                rate = base_rate * variation
                
                estimated_output = round(float(amount) * rate, 4)
                
                # Prepare swap info for button callback
                swap_info = {
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount": float(amount),
                    "estimated_output": estimated_output,
                    "chain": wallet_chain
                }
                
                # Create a unique ID for this swap
                swap_id = hashlib.md5(f"{user_id}:{from_token}:{to_token}:{amount}:{time.time()}".encode()).hexdigest()[:10]
                
                # Create buttons for swap options
                buttons = [
                    [
                        {"text": "✅ Approve Swap", "callback_data": f"swap_approve:{swap_id}"},
                        {"text": "❌ Cancel", "callback_data": f"swap_cancel:{swap_id}"}
                    ]
                ]
                
                # For testnets, provide additional explanation
                return {
                    "content": f"💱 **Swap Quote (Testnet)**\n\n" +
                        f"From: {amount} {from_token}\n" +
                        f"To: ~{estimated_output} {to_token}\n" +
                        f"Rate: 1 {from_token} = {rate} {to_token}\n" +
                        f"Network: {wallet_chain.replace('_', ' ').title()}\n" +
                        f"Fee: 0.3%\n\n" +
                        "_Note: This is a testnet swap and will use testnet tokens only. No real value will be exchanged._\n\n" +
                        "Do you want to proceed with this swap?",
                    "metadata": {
                        "telegram_buttons": buttons
                    },
                    "parse_mode": "Markdown",
                    "swap_data": {
                        "id": swap_id,
                        "details": swap_info
                    }
                }
            else:
                # For mainnet (not implemented)
                return {
                    "content": "⚠️ Mainnet swaps are not available in this version. Please use a testnet network for testing.\n\n" +
                              "Switch to a testnet using /network base_sepolia"
                }
                
        except Exception as e:
            logger.exception(f"Error processing swap request: {e}")
            return {
                "content": f"⚠️ There was an error processing your swap request: {str(e)}\n\n" +
                          "Please try again later or contact support if the problem persists."
            }

    async def _handle_disconnect_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /disconnect command to disconnect a wallet.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not wallet_address:
            return {
                "content": "You don't have a wallet connected. Use /connect to set up a wallet."
            }
            
        # If we have a wallet service, remove the wallet from it
        if self.wallet_service:
            try:
                await self.wallet_service.delete_wallet(
                    user_id=str(user_id),
                    platform="telegram"
                )
            except Exception as e:
                logger.exception(f"Error disconnecting wallet: {e}")
        
        return {
            "content": f"Wallet disconnected successfully. Your data has been removed from our service.\n\nUse /connect if you'd like to reconnect or create a new wallet.",
            "wallet_address": None  # Signal to remove the wallet
        }

    async def _handle_networks_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /networks command to show available networks.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not self.wallet_service:
            networks = [
                {"id": "scroll_sepolia", "name": "Scroll Sepolia", "description": "Scroll L2 testnet"},
                {"id": "base_sepolia", "name": "Base Sepolia", "description": "Base L2 testnet"},
                {"id": "ethereum_sepolia", "name": "Ethereum Sepolia", "description": "Ethereum testnet"}
            ]
        else:
            try:
                networks = await self.wallet_service.get_supported_chains()
            except Exception as e:
                logger.exception(f"Error getting networks: {e}")
                networks = []
                
        if not networks:
            return {
                "content": "No networks available at the moment. Please try again later."
            }
            
        # Create network buttons for selection
        buttons = []
        row = []
        
        # Get current network if user has a wallet
        current_network = DEFAULT_CHAIN
        if wallet_address and self.wallet_service:
            try:
                wallet_info = await self.wallet_service.get_wallet_info(str(user_id), "telegram")
                if wallet_info and "chain" in wallet_info:
                    current_network = wallet_info["chain"]
            except Exception as e:
                logger.exception(f"Error getting current network: {e}")
        
        # Format network list with buttons
        networks_text = "🌐 Available Networks:\n\n"
        
        for i, network in enumerate(networks):
            network_id = network["id"]
            network_name = network["name"]
            network_desc = network.get("description", "")
            
            # Mark current network
            current_marker = "✅ " if network_id == current_network else ""
            
            networks_text += f"{current_marker}**{network_name}** ({network_id})\n{network_desc}\n\n"
            
            # Add button for this network
            row.append({"text": network_name, "callback_data": f"select_network:{network_id}"})
            
            # Create rows of 2 buttons
            if len(row) == 2 or i == len(networks) - 1:
                buttons.append(row)
                row = []
        
        # Add instructions
        if wallet_address:
            networks_text += "Click a network below to switch, or use the command:\n/network [network_id]"
        else:
            networks_text += "Connect a wallet first with /connect to use these networks."
            buttons = []  # No buttons if no wallet
        
        return {
            "content": networks_text,
            "metadata": {
                "telegram_buttons": buttons
            } if buttons else None
        }

    async def _handle_network_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /network command to switch networks.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments (should be network name)
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not args:
            return {
                "content": "Please specify a network name. Example: /network base_sepolia\n\nUse /networks to see a list of available networks."
            }
        
        if not self.wallet_service:
            return {
                "content": "Network switching is not available in this version."
            }
        
        # Extract network name from args
        network_name = args.strip().lower()
        
        # If the user wrote network names like "Base Sepolia", convert to base_sepolia format
        network_name = network_name.replace(" ", "_")
        
        # Add check for common shorthand
        shorthand_mappings = {
            "scroll": "scroll_sepolia",
            "base": "base_sepolia",
            "ethereum": "ethereum_sepolia",
            "sepolia": "ethereum_sepolia"  # Assume regular sepolia is ethereum sepolia
        }
        
        network_name = shorthand_mappings.get(network_name, network_name)
        
        # Switch the network
        result = await self.wallet_service.switch_chain(
            user_id=str(user_id),
            platform="telegram",
            chain=network_name
        )
        
        if result["success"]:
            return {
                "content": f"🌐 Switched network to {result['chain_info']['name']} successfully!\n\nYou can now use other commands like /swap and /balance on this network."
            }
        else:
            available_chains = await self.wallet_service.get_supported_chains()
            network_list = ", ".join([chain["id"] for chain in available_chains])
            
            return {
                "content": f"❌ {result['message']}\n\nAvailable networks: {network_list}\n\nUse /networks to see details."
            }

    async def _handle_keys_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /keys command to explain key custody.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        # Create buttons for wallet management if they have a wallet
        buttons = []
        if wallet_address:
            buttons.append([
                {"text": "📱 Open Web App", "url": "https://snel-pointless.vercel.app"}
            ])
        
        # Check if we're using SmartWalletService or WalletService
        is_smart_wallet = isinstance(self.wallet_service, SmartWalletService)
        
        if is_smart_wallet:
            # Coinbase CDP wallet information
            return {
                "content": "🔐 **Key Custody & Security**\n\n" +
                    "Your wallet security is our priority. Here's how it works:\n\n" +
                    "• Your wallet is powered by Coinbase Developer Platform (CDP)\n" +
                    "• CDP creates an ERC-4337 compatible smart wallet for you\n" +
                    "• Your private keys are securely managed by CDP\n" +
                    "• The wallet uses Account Abstraction technology for improved security and usability\n" +
                    "• YOU maintain full control of your wallet through your Telegram account\n" +
                    "• Our bot NEVER has access to your private keys\n\n" +
                    "For full wallet management including advanced features, please use our web interface at:\n" +
                    "https://snel-pointless.vercel.app\n\n" +
                    "There you can access the full Coinbase CDP dashboard to manage all aspects of your wallet security.",
                "metadata": {
                    "telegram_buttons": buttons
                } if buttons else None
            }
        else:
            # Legacy/simulated wallet information
            return {
                "content": "🔐 **Key Custody & Security**\n\n" +
                    "Your wallet security is our priority. Here's how it works:\n\n" +
                    "• You're currently using a simulated wallet for testing\n" +
                    "• For a real wallet with improved security, you'll need to upgrade\n" +
                    "• Real wallets use Coinbase CDP technology with ERC-4337 Account Abstraction\n" +
                    "• Simulated wallets are perfect for learning but aren't suitable for real assets\n\n" +
                    "For full wallet management including advanced features, please use our web interface at:\n" +
                    "https://snel-pointless.vercel.app",
                "metadata": {
                    "telegram_buttons": buttons
                } if buttons else None
            }

    async def _handle_faucet_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle /faucet command to get testnet ETH.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments (unused)
            wallet_address: User's wallet address if available
            
        Returns:
            Dict with response content
        """
        try:
            # Get wallet data
            wallet_data = await self.wallet_service.get_smart_wallet(user_id, platform="telegram")
            
            if not wallet_data or not wallet_data.get("address"):
                return {
                    "content": "⚠️ You don't have a wallet yet. Please use /connect to create one."
                }
            
            # Get wallet address
            address = wallet_data.get("address")
            chain = wallet_data.get("chain", "base_sepolia")
            
            # Get chain info for display
            chain_info = {
                "name": chain.replace("_", " ").title(),
                "is_testnet": "sepolia" in chain or "goerli" in chain
            }
            
            # Check if this is a testnet wallet
            if not chain_info.get("is_testnet", False):
                return {
                    "content": "⚠️ Your wallet is on a mainnet network. Faucets are only available for testnet networks."
                }
            
            # Try to get ETH from CDP faucet
            faucet_result = await self.wallet_service.fund_wallet_from_faucet(user_id, platform="telegram")
            
            if faucet_result.get("success"):
                # Success!
                tx_hash = faucet_result.get("transaction_hash", "")
                explorer_link = f"https://sepolia.basescan.org/tx/{tx_hash}" if "base" in chain else f"https://sepolia.etherscan.io/tx/{tx_hash}"
                
                message = f"🎉 Testnet ETH has been requested for your wallet!\n\n"
                message += f"📬 Wallet: `{address}`\n"
                message += f"🔗 Network: {chain_info.get('name')}\n\n"
                
                if tx_hash:
                    message += f"See transaction on block explorer:\n[View Transaction]({explorer_link})\n\n"
                
                message += "The ETH should arrive in your wallet within a few minutes. Use /balance to check your balance."
                
                return {
                    "content": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }
            else:
                # If built-in faucet fails, provide alternative faucet links
                faucet_url = ""
                if "base_sepolia" in chain:
                    faucet_url = "https://www.coinbase.com/faucets/base-sepolia-faucet"
                elif "ethereum_sepolia" in chain:
                    faucet_url = "https://www.alchemy.com/faucets/ethereum-sepolia"
                    
                error_msg = faucet_result.get("error", "Unknown error")
                
                message = f"❌ Unable to automatically fetch testnet ETH: {error_msg}\n\n"
                message += f"📬 Your wallet address: `{address}`\n"
                message += f"🔗 Network: {chain_info.get('name')}\n\n"
                message += "Please try an external faucet instead:\n\n"
                
                if faucet_url:
                    message += f"1. Visit {faucet_url}\n"
                    message += f"2. Enter your wallet address: `{address}`\n"
                    message += "3. Complete any verification steps\n\n"
                else:
                    message += "Please search for a faucet for your current network.\n\n"
                    
                message += "After getting ETH, use /balance to check your wallet balance."
                
                buttons = [
                    [
                        {"text": "🔄 Check Balance", "callback_data": "check_balance"}
                    ]
                ]
                
                return {
                    "content": message,
                    "buttons": buttons,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": False
                }
        except Exception as e:
            logger.exception(f"Error getting testnet ETH: {e}")
            return {
                "content": f"❌ There was an error getting testnet ETH: {str(e)}\n\nPlease try again later."
            }

    async def process_callback_query(
        self,
        user_id: str,
        callback_data: str,
        wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a callback query from Telegram.
        
        Args:
            user_id: Telegram user ID
            callback_data: The callback data from the button
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content and any additional information
        """
        logger.info(f"Processing callback query from user {user_id}: {callback_data}")
        
        return await self._process_callback_query(
            user_id=user_id,
            callback_data=callback_data,
            wallet_address=wallet_address
        )

    async def process_command(
        self,
        command: str,
        args: str,
        user_id: str,
        wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a command from Telegram.
        
        Args:
            command: The command (e.g., /start, /help)
            args: Command arguments
            user_id: Telegram user ID
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content and any additional information
        """
        logger.info(f"Processing command: {command} with args: {args} for user {user_id}")
        
        # Handle all commands that start with a /
        if command.startswith('/'):
            # Remove the / prefix
            command_name = command[1:]
            
            # Check if we have a handler for this command
            if command_name in self.command_handlers:
                handler = self.command_handlers[command_name]
                logger.info(f"Executing handler for command: {command_name}")
                
                # Execute the handler
                response = await handler(user_id, args, wallet_address)
                
                # Add personality to the response
                if "content" in response:
                    response["content"] = self._add_telegram_personality(response["content"])
                    
                return response
            else:
                # Unknown command
                return {
                    "content": f"I don't recognize the command '{command}'. Type /help to see available commands."
                }
        
        # Not a command
        return {
            "content": "This doesn't look like a command. Try /help to see what I can do!"
        }

    async def _handle_test_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the test command to verify command processing works."""
        logger.info(f"Test command executed by user {user_id} with args: {args}")
        return {
            "content": f"👋 Hello! The test command is working. You sent: '{args}'"
        }

    async def process_message(
        self,
        message: str,
        platform: str,
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message from a messaging platform.
        
        This method handles parsing the message and generating a response.
        
        Args:
            message: The message text to process
            platform: The messaging platform (e.g., "telegram", "whatsapp")
            user_id: The user ID on the messaging platform
            wallet_address: The user's wallet address if connected
            metadata: Additional metadata for processing (optional)
            
        Returns:
            A dictionary with the response content and any additional information
        """
        # Process AI queries if this isn't a command or transaction
        if self.gemini_service and self._is_general_question(message):
            try:
                logger.info(f"Processing message as general question: '{message}'")
                wallet_info = None
                if wallet_address:
                    wallet_info = {"wallet_address": wallet_address}
                    
                # Call Gemini for AI-powered response
                ai_response = await self.gemini_service.answer_crypto_question(
                    user_query=message,
                    wallet_info=wallet_info
                )
                logger.info(f"Gemini response: {ai_response[:100]}...")
                
                return {
                    "content": ai_response,
                    "wallet_address": wallet_address
                }
            except Exception as e:
                logger.exception(f"Error generating AI response: {e}")
                # Continue with normal processing if AI fails
        
        # For MVP, just return a default response
        return await super().process_message(
            message=message,
            platform=platform, 
            user_id=user_id,
            wallet_address=wallet_address,
            metadata=metadata
        ) 

    def _is_general_question(self, message: str) -> bool:
        """
        Determine if a message is a general question that should be handled by AI.
        
        Args:
            message: The message text to analyze
            
        Returns:
            True if this appears to be a general question, False if it's a command or transaction
        """
        # If it starts with /, it's a command
        if message.startswith('/'):
            return False
            
        # Check for specific transaction formats/keywords that should be handled by specific commands
        transaction_keywords = [
            'swap', 'transfer', 'send', 'bridge', 
            'buy', 'sell', 'trade', 'exchange'
        ]
        
        # Skip short messages like "hi" or "hello"
        if len(message.split()) <= 2:
            return False
            
        # Look for transaction-like messages that should be handled by specific commands
        message_lower = message.lower()
        
        for keyword in transaction_keywords:
            if keyword in message_lower and any(char.isdigit() for char in message):
                # Likely a transaction request with an amount
                return False
                
        # If we got here, it's probably a general question
        return True 

    async def _approve_swap(self, user_id: str, swap_id: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a swap approval from an inline button.
        
        Args:
            user_id: Telegram user ID
            swap_id: ID of the swap to approve
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        logger.info(f"Processing swap approval for swap ID: {swap_id}")
        
        if not wallet_address:
            return {
                "content": "⚠️ You need to connect a wallet first. Use /connect to set up your wallet."
            }
        
        # For now, we'll simulate the swap process on testnet
        try:
            # Get the user's wallet details
            wallet_data = await self.wallet_service.get_smart_wallet(user_id, platform="telegram")
            wallet_chain = wallet_data.get("chain", "base_sepolia")
            
            # Check if this is a testnet
            is_testnet = "sepolia" in wallet_chain or "goerli" in wallet_chain
            
            if not is_testnet:
                return {
                    "content": "⚠️ Mainnet swaps are not available in this version. Please use a testnet network for testing."
                }
            
            # Generate a fake transaction hash
            tx_hash = f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
            
            # Create a block explorer link based on the chain
            explorer_url = ""
            if "base_sepolia" in wallet_chain:
                explorer_url = f"https://sepolia.basescan.org/tx/{tx_hash}"
            elif "ethereum_sepolia" in wallet_chain:
                explorer_url = f"https://sepolia.etherscan.io/tx/{tx_hash}"
            elif "scroll_sepolia" in wallet_chain:
                explorer_url = f"https://sepolia-blockscout.scroll.io/tx/{tx_hash}"
            
            # Create buttons for checking balance or doing another swap
            buttons = [
                [
                    {"text": "🔄 Check Balance", "callback_data": "check_balance"},
                    {"text": "💱 New Swap", "callback_data": "suggest_swap"}
                ]
            ]
            
            # Add explorer button if available
            if explorer_url:
                buttons.append([
                    {"text": "🔍 View Transaction", "url": explorer_url}
                ])
            
            return {
                "content": f"✅ **Swap Successfully Simulated!**\n\n" +
                           f"This was a testnet swap demonstration.\n\n" +
                           f"Transaction Hash: `{tx_hash}`\n" +
                           f"Network: {wallet_chain.replace('_', ' ').title()}\n\n" +
                           f"_Note: No actual tokens were swapped as this is a testnet demo._\n\n" +
                           f"You can check your balance or initiate a new swap using the buttons below.",
                "metadata": {
                    "telegram_buttons": buttons
                },
                "parse_mode": "Markdown"
            }
        except Exception as e:
            logger.exception(f"Error approving swap: {e}")
            return {
                "content": f"⚠️ There was an error processing your swap: {str(e)}\n\nPlease try again later."
            }
    
    async def _cancel_swap(self, user_id: str, swap_id: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a swap cancellation from an inline button.
        
        Args:
            user_id: Telegram user ID
            swap_id: ID of the swap to cancel
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        logger.info(f"Cancelling swap with ID: {swap_id}")
        
        # Create buttons for checking balance or initiating a new swap
        buttons = [
            [
                {"text": "🔄 Check Balance", "callback_data": "check_balance"},
                {"text": "💱 New Swap", "callback_data": "suggest_swap"}
            ]
        ]
        
        return {
            "content": "❌ Swap cancelled. No tokens were exchanged.\n\nYou can check your balance or initiate a new swap using the buttons below.",
            "metadata": {
                "telegram_buttons": buttons
            }
        } 