"""
Telegram-specific agent for handling Telegram bot interactions.
"""
import logging
import json
import re
import random
import hashlib
import time
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from pydantic import Field
from app.agents.messaging_agent import MessagingAgent
from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.wallet_service import WalletService
from app.services.gemini_service import GeminiService
from app.services.prices import price_service

logger = logging.getLogger(__name__)

# Default blockchain network
DEFAULT_CHAIN = "scroll_sepolia"

class TelegramAgent(MessagingAgent):
    """
    Agent for handling Telegram-specific interactions.
    
    This agent extends the MessagingAgent with Telegram-specific features
    like commands, wallet creation, and inline buttons.
    """
    command_handlers: Dict[str, Callable] = Field(default_factory=dict)
    wallet_service: Optional[WalletService] = None
    gemini_service: Optional[GeminiService] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(
        self, 
        token_service: TokenService, 
        swap_service: SwapService,
        wallet_service: Optional[WalletService] = None,
        gemini_service: Optional[GeminiService] = None
    ):
        """
        Initialize the Telegram agent.
        
        Args:
            token_service: Service for token lookups
            swap_service: Service for swap operations
            wallet_service: Service for wallet operations
            gemini_service: Service for AI-powered responses
        """
        # Initialize the parent class
        super().__init__(token_service=token_service, swap_service=swap_service)
        
        # Store the services
        self.wallet_service = wallet_service
        self.gemini_service = gemini_service
        
        # Logging for debugging
        logger.info(f"TelegramAgent initialized with wallet_service: {wallet_service is not None}")
        logger.info(f"TelegramAgent initialized with gemini_service: {gemini_service is not None}")
        
        # Command handlers mapping
        self.command_handlers = {
            "/start": self._handle_start_command,
            "/help": self._handle_help_command,
            "/connect": self._handle_connect_command,
            "/balance": self._handle_balance_command,
            "/price": self._handle_price_command,
            "/swap": self._handle_swap_command,
            "/disconnect": self._handle_disconnect_command,
            "/networks": self._handle_networks_command,
            "/network": self._handle_network_command,
            "/keys": self._handle_keys_command
        }

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
        
        # Handle different types of updates
        if "message" in update and "text" in update["message"]:
            message_text = update["message"]["text"]
            return await self._process_telegram_message(message_text, user_id, wallet_address, metadata)
        elif "callback_query" in update:
            # Handle button callbacks
            callback_data = update["callback_query"]["data"]
            return await self._process_callback_query(user_id, callback_data, wallet_address)
        else:
            # Default response for unsupported update types
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
            command = command_parts[0].lower()
            args = command_parts[1] if len(command_parts) > 1 else ""
            
            # Dispatch to the appropriate command handler
            if command in self.command_handlers:
                return await self.command_handlers[command](user_id, args, wallet_address)
            else:
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
        Process a callback query from Telegram inline buttons.
        
        Args:
            user_id: Telegram user ID
            callback_data: The callback data from the button
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content and any additional information
        """
        # Simple callbacks that map to existing command handlers
        callback_to_command = {
            "check_balance": self._handle_balance_command,
            "show_help": self._handle_help_command,
            "show_networks": self._handle_networks_command,
        }
        
        # Log the callback for debugging
        logger.info(f"Processing callback from user {user_id}: {callback_data}")
        
        if callback_data in callback_to_command:
            logger.info(f"Executing mapped command handler for {callback_data}")
            return await callback_to_command[callback_data](user_id, "", wallet_address)
        
        # Handle network selection
        if callback_data.startswith("select_network:"):
            network_id = callback_data.split(":", 1)[1]
            logger.info(f"Switching network to {network_id} for user {user_id}")
            
            if not self.wallet_service:
                return {
                    "content": "Network switching is not available in this version."
                }
                
            # Call the wallet service to switch chains
            result = await self.wallet_service.switch_chain(
                user_id=str(user_id),
                platform="telegram",
                chain=network_id
            )
            
            if result["success"]:
                return {
                    "content": f"🌐 Switched network to {result['chain_info']['name']} successfully!\n\nYou can now use other commands like /swap and /balance on this network."
                }
            else:
                return {
                    "content": f"❌ Error switching network: {result['message']}"
                }
        
        # Handle swap approval
        if callback_data.startswith("approve_swap:"):
            try:
                swap_info_str = callback_data.split(":", 1)[1]
                swap_info = json.loads(swap_info_str)
                
                # Log the swap for debugging
                logger.info(f"Approving swap for user {user_id}: {swap_info}")
                
                # TODO: In a real implementation, this would call the swap service
                # For MVP, just simulate the swap being successful
                
                return {
                    "content": f"🔄 Swap executed successfully!\n\n" +
                        f"Swapped {swap_info['amount']} {swap_info['from_token']} " +
                        f"for {swap_info['estimated_output']} {swap_info['to_token']}\n\n" +
                        f"Transaction hash: 0x{hashlib.sha256(f'{time.time()}'.encode()).hexdigest()[:32]}\n\n" +
                        f"Your updated balance will be available shortly."
                }
            except Exception as e:
                logger.exception(f"Error processing swap approval: {e}")
                return {
                    "content": "❌ Something went wrong processing your swap. Please try again."
                }
                
        # Handle swap cancellation
        if callback_data == "cancel_swap":
            return {
                "content": "Swap cancelled. Your funds remain unchanged."
            }
            
        # Handle create wallet callback - directly call the connect command
        if callback_data == "create_wallet":
            return await self._handle_connect_command(user_id, "", None)
            
        # Handle suggestions for the user
        if callback_data == "suggest_swap":
            return {
                "content": "To swap tokens, use the /swap command followed by the amount, token you want to swap, and token you want to receive.\n\n" +
                    "Example: `/swap 0.1 ETH for USDC`\n\n" +
                    "Currently swaps work on Scroll Sepolia testnet."
            }
            
        # Default response for unknown callbacks
        return {
            "content": "I'm not sure how to handle that request. Please try using the main commands like /help or /balance."
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
                result = emoji + " " + content
                
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
            buttons.append([
                {"text": "💰 Check Balance", "callback_data": "check_balance"},
                {"text": "🌐 Switch Network", "callback_data": "show_networks"}
            ])
            buttons.append([
                {"text": "📊 Price Check", "callback_data": "suggest_price"},
                {"text": "🔄 Swap Tokens", "callback_data": "suggest_swap"}
            ])
            
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
        
        # Create help text
        help_text = "🐌 **Snel DeFi Assistant Commands:**\n\n"
        
        # Wallet commands
        help_text += "**Wallet Commands:**\n"
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
        # Check for the "force" parameter to force creating a new wallet
        force_new = "force" in args.lower()
        
        # If the user already has a wallet and isn't forcing a new one
        if wallet_address and not force_new:
            return {
                "content": f"You already have a wallet connected: `{wallet_address}`\n\n" +
                           "To disconnect this wallet, use */disconnect*\n" +
                           "To force create a new wallet, use */connect force*"
            }
            
        # If force_new and an existing wallet, disconnect it first
        if force_new and wallet_address and self.wallet_service:
            try:
                await self.wallet_service.delete_wallet(
                    user_id=str(user_id),
                    platform="telegram"
                )
                wallet_address = None
                logger.info(f"Forced disconnect of wallet for user {user_id}")
            except Exception as e:
                logger.exception(f"Error disconnecting wallet during force connect: {e}")
            
        # Check if user already has a wallet in the database (and we're not forcing a new one)
        existing_wallet = None
        if not force_new and self.wallet_service:
            try:
                wallet_info = await self.wallet_service.get_wallet_info(
                    user_id=str(user_id), 
                    platform="telegram"
                )
                
                if wallet_info and "wallet_address" in wallet_info:
                    existing_wallet = wallet_info["wallet_address"]
                    
                    return {
                        "content": f"Welcome back! I've reconnected your existing wallet: `{existing_wallet}`\n\n" +
                                  "Use */balance* to check your balance or */networks* to switch networks.\n\n" +
                                  "To create a new wallet instead, use */connect force*",
                        "wallet_address": existing_wallet
                    }
            except Exception as e:
                logger.exception(f"Error checking for existing wallet: {e}")
        
        # Particle Auth is required for wallet creation
        if not self.wallet_service:
            return {
                "content": "Sorry, wallet services are not available at the moment. Please try again later."
            }
            
        # Create a new Particle Auth wallet
        try:
            wallet_result = await self.wallet_service.create_wallet(
                user_id=str(user_id),
                platform="telegram",
                wallet_address=None,  # Force creation of a new wallet
                chain=DEFAULT_CHAIN
            )
            
            if not wallet_result.get("success"):
                return {
                    "content": f"❌ Error creating wallet: {wallet_result.get('message', 'Unknown error')}\n\n" +
                              "Please try again later or contact support."
                }
                
            new_wallet_address = wallet_result.get("wallet_address")
            wallet_type = wallet_result.get("wallet_type", "particle")
            
            # Create buttons to guide next steps
            buttons = [
                [
                    {"text": "💰 Check Balance", "callback_data": "check_balance"},
                    {"text": "🌐 Switch Network", "callback_data": "show_networks"}
                ],
                [
                    {"text": "🔄 Swap Tokens", "callback_data": "suggest_swap"},
                    {"text": "ℹ️ Help", "callback_data": "show_help"}
                ]
            ]
            
            return {
                "content": f"✅ Your Particle Auth wallet has been created!\n\n" +
                    f"Wallet Address: `{new_wallet_address}`\n\n" +
                    f"This is a **secure smart contract wallet** powered by Particle Auth. It allows you to:\n\n" +
                    f"• Execute real on-chain transactions\n" +
                    f"• Securely manage your assets\n" +
                    f"• Use advanced features like batched transactions\n\n" +
                    f"What would you like to do with your wallet?",
                "metadata": {
                    "telegram_buttons": buttons
                },
                "wallet_address": new_wallet_address
            }
            
        except Exception as e:
            logger.exception(f"Error creating wallet: {e}")
            return {
                "content": "❌ Sorry, there was an error creating your wallet. Please try again later."
            }

    async def _handle_balance_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /balance command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not wallet_address:
            return {
                "content": "You need to connect a wallet first. Use /connect to set up your wallet."
            }
            
        # Get user's current network if using wallet service
        current_network = "Scroll Sepolia"
        chain_id = "scroll_sepolia"
        numeric_chain_id = 534351  # Default to Scroll Sepolia
        wallet_info = None
        
        if self.wallet_service:
            try:
                wallet_info = await self.wallet_service.get_wallet_info(str(user_id), "telegram")
                if wallet_info and "chain_info" in wallet_info:
                    current_network = wallet_info["chain_info"].get("name", "Scroll Sepolia")
                    chain_id = wallet_info.get("chain", "scroll_sepolia")
                    numeric_chain_id = wallet_info["chain_info"].get("chainId", 534351)
            except Exception as e:
                logger.exception(f"Error getting wallet network: {e}")
        
        # Try to get real balances from Brian API
        has_balance_data = False
        balances = {}
        balance_items = []
        total_usd_value = 0
        
        if self.token_service and hasattr(self.token_service, "brian_service"):
            try:
                brian_service = self.token_service.brian_service
                balance_result = await brian_service.get_token_balances(
                    wallet_address=wallet_address,
                    chain_id=numeric_chain_id
                )
                
                if balance_result and "answer" in balance_result:
                    # Try to extract structured balance data from the Brian API response
                    answer = balance_result.get("answer", "")
                    
                    # Look for patterns like "0.1 ETH ($200.00)" in the response
                    token_pattern = r"(\d+\.?\d*)\s+([A-Za-z]+)\s+\(\$(\d+\.?\d*)\)"
                    matches = re.findall(token_pattern, answer)
                    
                    if matches:
                        # We found structured balance data, parse it
                        for amount_str, token, usd_str in matches:
                            amount = float(amount_str)
                            usd_value = float(usd_str)
                            
                            balances[token.lower()] = amount
                            total_usd_value += usd_value
                            
                            # Format token amount based on type
                            if token.lower() == "eth":
                                token_display = f"{amount:.4f} ETH"
                            else:
                                token_display = f"{amount:.2f} {token.upper()}"
                                
                            # Format USD value
                            usd_display = f"(${usd_value:.2f})"
                            
                            balance_items.append(f"{token_display} {usd_display}")
                            
                        has_balance_data = len(balance_items) > 0
                    else:
                        # If we couldn't extract structured data, show the raw answer
                        logger.info(f"No structured balance data found in: {answer}")
            except Exception as e:
                logger.exception(f"Error getting real balances: {e}")
                
        # If we couldn't get real balances, show an error message
        if not has_balance_data:
            # Create buttons for actions
            buttons = [
                [
                    {"text": "🌐 Switch Network", "callback_data": "show_networks"},
                    {"text": "🔄 Retry Balance", "callback_data": "check_balance"}
                ]
            ]
            
            return {
                "content": f"📊 **Wallet Balance on {current_network}**\n\n" +
                    f"Wallet: `{wallet_address}`\n\n" +
                    f"Unable to retrieve wallet balance data at this time. This could be due to:\n\n" +
                    f"• Network connectivity issues\n" +
                    f"• API rate limits\n" +
                    f"• No tokens in this wallet\n\n" +
                    f"Please try again later or switch to a different network.",
                "metadata": {
                    "telegram_buttons": buttons
                }
            }
        
        # Create buttons for actions
        buttons = [
            [
                {"text": "🔄 Swap Tokens", "callback_data": "suggest_swap"},
                {"text": "🌐 Switch Network", "callback_data": "show_networks"}
            ]
        ]
        
        # Create balance display message
        message = f"💰 **Wallet Balance on {current_network}**\n\n"
        message += f"Wallet: `{wallet_address}`\n\n"
        
        if balance_items:
            message += "**Tokens:**\n"
            for item in balance_items:
                message += f"• {item}\n"
            message += f"\n**Total Value:** ${total_usd_value:.2f}\n\n"
        else:
            message += "No tokens found in this wallet.\n\n"
        
        return {
            "content": message,
            "metadata": {
                "telegram_buttons": buttons
            }
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
            price_data = await price_service.get_token_price(token_symbol)
            
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
        
        # For MVP, simulate getting a quote
        estimated_output = round(float(amount) * (random.random() * 0.2 + 0.9) * 1800, 2)
        
        # Prepare swap info for button callback
        swap_info = {
            "from_token": from_token.upper(),
            "to_token": to_token.upper(),
            "amount": float(amount),
            "estimated_output": estimated_output
        }
        
        # Create buttons for swap options
        buttons = [
            [
                {"text": "✅ Approve Swap", "callback_data": f"approve_swap:{json.dumps(swap_info)}"},
                {"text": "❌ Cancel", "callback_data": "cancel_swap"}
            ]
        ]
        
        return {
            "content": f"Swap Quote:\n\n" +
                f"From: {amount} {from_token.upper()}\n" +
                f"To: ~{estimated_output} {to_token.upper()}\n" +
                f"Fee: 0.3%\n\n" +
                f"Do you want to proceed with this swap?",
            "metadata": {
                "telegram_buttons": buttons
            }
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

    async def _generate_wallet_address(self, user_id: str) -> str:
        """
        Generate a wallet address for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            A wallet address string
        """
        # Use the wallet service to create a real wallet if possible
        if self.wallet_service:
            try:
                # Create a wallet with Particle Auth
                result = await self.wallet_service.create_wallet(
                    user_id=user_id,
                    platform="telegram",
                    wallet_address=None,  # Let the service create a new address
                    chain=DEFAULT_CHAIN
                )
                
                if result.get("success"):
                    logger.info(f"Created wallet for user {user_id}: {result.get('wallet_address')} ({result.get('wallet_type')})")
                    return result.get("wallet_address")
                else:
                    logger.error(f"Failed to create wallet: {result.get('message')}")
                    # Return a user-friendly error, but this shouldn't occur in normal flow
                    raise ValueError(f"Failed to create wallet: {result.get('message')}")
            except Exception as e:
                logger.exception(f"Error creating wallet: {e}")
                raise
        else:
            # No wallet service - shouldn't happen in normal flow
            logger.error("No wallet service available")
            raise ValueError("Wallet service is unavailable")

    async def process_message(
        self,
        message: str,
        platform: str,
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a general message and provide a response."""
        # First check for command-like patterns (but not actual commands)
        if not message.startswith('/') and self.gemini_service:
            # Check for specific transaction-related patterns
            transaction_patterns = [
                r"(?:swap|buy|sell|trade|exchange) .+",
                r"(?:send|transfer) .+ to .+",
                r"(?:bridge) .+ from .+ to .+",
            ]
            
            if wallet_address and any(re.search(pattern, message.lower()) for pattern in transaction_patterns):
                return {
                    "content": "🐌 I noticed you might want to do a transaction. Try using one of these command formats:\n\n" +
                        "For swaps: */swap 0.1 ETH for USDC*\n" +
                        "For transfers: */send 10 USDC to 0xAddress*\n" +
                        "For bridges: */bridge 0.1 ETH from Scroll to Base*\n\n" +
                        "This makes it easier for me to understand exactly what you want to do."
                }
            
            # Get basic wallet info for context
            wallet_info = None
            if wallet_address:
                wallet_info = {
                    "address": wallet_address,
                    "connected": True
                }
            
            # Use Gemini for non-command queries
            try:
                # Generate response with Gemini
                gemini_response = await self.gemini_service.answer_crypto_question(message, wallet_info)
                
                # Add personality flair
                final_response = self._add_telegram_personality(gemini_response)
                
                return {
                    "content": final_response
                }
            except Exception as e:
                logger.exception(f"Error using Gemini: {e}")
                # Provide a helpful fallback response
                if not wallet_address:
                    return {
                        "content": "🐌 I noticed you don't have a wallet connected yet. Let's fix that!\n\n" +
                                  "Type */connect* to create or connect a wallet. This will let you check your balance, swap tokens, and more.\n\n" +
                                  "If you just want to check info without a wallet, you can try:\n" +
                                  "🔹 */price ETH* - Check token prices\n" +
                                  "🔹 */networks* - See available networks\n" +
                                  "🔹 */help* - See all commands"
                    }
                # Fall through to general help response below
                
        # Check for general "what can you do" type questions
        what_can_do_patterns = [
            r"what.+can.+you.+do",
            r"what.+do.+you.+do",
            r"help.+me",
            r"how.+to.+use",
            r"what.+is.+this",
            r"(?:^|\s+)help(?:\s+|$)",
            r"commands",
            r"features",
            r"gm",
            r"hello",
            r"hi"
        ]
        
        for pattern in what_can_do_patterns:
            if re.search(pattern, message.lower()):
                return {
                    "content": "🐌 Hello there! I'm Snel, your DeFi assistant. Here's what I can do for you:\n\n" +
                        "🔹 */connect* - Create or connect a wallet\n" +
                        "🔹 */price ETH* - Check token prices\n" +
                        "🔹 */swap 0.1 ETH for USDC* - Swap tokens\n" +
                        "🔹 */balance* - Check your wallet balance\n" +
                        "🔹 */network sepolia* - Switch to a network\n" +
                        "🔹 */networks* - See available networks\n" +
                        "🔹 */keys* - Learn about key management\n" +
                        "🔹 */help* - See all commands\n\n" +
                        "Try one of these commands to get started! Just tap on a command or type it.\n\n" +
                        "Or ask me something like \"What's the price of Bitcoin?\" or \"Tell me about Scroll L2\"."
                }
            
        try:
            # Original implementation for other message types
            result = await super().process_message(
                message=message,
                platform=platform,
                user_id=user_id,
                wallet_address=wallet_address,
                metadata=metadata
            )
            
            return result
        except Exception as e:
            logger.exception(f"Error in parent process_message: {e}")
            # Provide a fallback response if all else fails
            if not wallet_address:
                return {
                    "content": "🐌 Hello! To get started with me, you'll need to connect a wallet using */connect* command.\n\n" +
                              "Or you can check information like token prices using */price ETH*"
                }
            return {
                "content": "🐌 I'm not sure how to respond to that. Try one of these commands:\n\n" +
                          "*/help* - See all available commands\n" +
                          "*/price ETH* - Check token prices\n" +
                          "*/balance* - Check your wallet balance"
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
        
        return {
            "content": "🔐 **Key Custody & Security**\n\n" +
                "Your wallet security is our priority. Here's how it works:\n\n" +
                "• Your keys are generated and managed by Particle Auth using MPC technology\n" +
                "• Private keys are never fully stored in one place - they're split across multiple secure locations\n" +
                "• YOU maintain full control of your wallet through a combination of your Telegram account and Particle Auth\n" +
                "• Our bot NEVER has access to your complete private keys\n\n" +
                "For full wallet management including exporting keys, please use our web interface at:\n" +
                "https://snel-pointless.vercel.app\n\n" +
                "There you can connect to the Particle Auth dashboard to manage all aspects of your wallet security.",
            "metadata": {
                "telegram_buttons": buttons
            } if buttons else None
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