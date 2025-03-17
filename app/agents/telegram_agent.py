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
from app.services.prices import price_service

logger = logging.getLogger(__name__)

class TelegramAgent(MessagingAgent):
    """
    Agent for handling Telegram-specific interactions.
    
    This agent extends the MessagingAgent with Telegram-specific features
    like commands, wallet creation, and inline buttons.
    """
    command_handlers: Dict[str, Callable] = Field(default_factory=dict)
    
    def __init__(self, token_service: TokenService, swap_service: SwapService):
        """
        Initialize the Telegram agent.
        
        Args:
            token_service: Service for token lookups
            swap_service: Service for swap operations
        """
        # Initialize the parent class
        super().__init__(token_service=token_service, swap_service=swap_service)
        
        # Command handlers mapping
        self.command_handlers = {
            "/start": self._handle_start_command,
            "/help": self._handle_help_command,
            "/connect": self._handle_connect_command,
            "/balance": self._handle_balance_command,
            "/price": self._handle_price_command,
            "/swap": self._handle_swap_command,
            "/disconnect": self._handle_disconnect_command
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
            return await self._process_callback_query(callback_data, user_id, wallet_address, metadata)
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
        callback_data: str,
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a callback query from Telegram inline buttons.
        
        Args:
            callback_data: Button callback data
            user_id: Telegram user ID
            wallet_address: User's wallet address if already connected
            metadata: Additional metadata
            
        Returns:
            Dict with response content and any additional information
        """
        if callback_data == "create_wallet":
            # Generate a deterministic wallet address
            new_wallet = self._generate_wallet_address(user_id)
            
            return {
                "content": f"🎉 I've created a simulated wallet for you!\n\n" +
                    f"Address: {new_wallet}\n\n" +
                    f"This is currently a simulated wallet for testing. Soon, we'll implement real smart contract wallets using Account Abstraction that will allow you to:\n\n" +
                    f"• Execute actual on-chain transactions\n" +
                    f"• Manage your assets securely\n" +
                    f"• Use advanced features like ERC-4337\n\n" +
                    f"For now, you can use this simulated wallet to test the interface and features.",
                "wallet_address": new_wallet
            }
        elif callback_data == "connect_existing":
            return {
                "content": "To connect an existing wallet, you would scan a QR code or enter your wallet address.\n\nThis feature will be implemented in the next version."
            }
        elif callback_data.startswith("approve_swap:"):
            # Extract swap information from callback data
            try:
                swap_info = json.loads(callback_data.replace("approve_swap:", ""))
                
                # Generate a fake transaction hash
                tx_hash = f"0x{hashlib.sha256(f'{user_id}:{int(time.time())}'.encode()).hexdigest()[:40]}"
                
                return {
                    "content": f"✅ Swap approved!\n\nSwapping {swap_info['amount']} {swap_info['from_token']} for ~{swap_info['estimated_output']} {swap_info['to_token']}\n\nTransaction hash: {tx_hash}\n\nThis is a simulation for the MVP. In the full version, this would execute the actual swap transaction."
                }
            except Exception as e:
                logger.error(f"Error processing swap approval: {e}")
                return {
                    "content": "Sorry, I couldn't process this swap request. Please try again with a new /swap command."
                }
        elif callback_data == "cancel_swap":
            return {
                "content": "Swap cancelled."
            }
        else:
            return {
                "content": "I don't know how to handle this action. Please try a different option."
            }

    def _add_telegram_personality(self, content: str) -> str:
        """
        Add Telegram-specific personality to the response.
        
        Args:
            content: Original response content
            
        Returns:
            Enhanced content with Telegram personality
        """
        # Add snail emojis occasionally
        snail_emojis = ["🐌", "🐌 ", "🐌💨", "🐢"]
        emoji_chance = 0.4  # Increased chance
        
        # Add occasional quips about being slow
        slow_quips = [
            "\n\n(Sorry for the delay, moving as fast as my shell allows!)",
            "\n\n(Zooming at snail speed...)",
            "\n\n(I might be slow, but I'll get you there safely!)",
            "\n\n(Taking my time to get things right! 🐌)",
            "\n\n(Slow and steady wins the DeFi race!)",
            ""  # Empty string for cases where we don't add a quip
        ]
        
        # Smart emoji placement - avoid adding to error messages or command syntax
        if not any(error_term in content.lower() for error_term in ["error", "sorry", "couldn't", "failed"]):
            if random.random() < emoji_chance and not content.startswith("🐌"):
                content = f"{random.choice(snail_emojis)} {content}"
        
        # More nuanced quip addition - add personality to successful responses
        if random.random() < 0.25 and len(content) > 50:
            content = f"{content} {random.choice(slow_quips)}"
        
        # Format command suggestions to make them more visible
        # This makes the commands clickable in Telegram
        content = re.sub(r'(\/[a-z]+)($|\s)', r'*\1*\2', content)
        
        return content

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
        return {
            "content": "👋 Welcome to Snel! I'm your DeFi assistant on Telegram.\n\n" +
                "I'm a Scroll-native multichain agent that can help you with:\n" +
                "• Checking token prices\n" +
                "• Swapping tokens across chains\n" +
                "• Managing your wallet\n" +
                "• Executing transactions\n\n" +
                "Try /help to see available commands, or visit our web app at https://snel-pointless.vercel.app/\n\n" +
                "🐌 I might be slow, but I'll get you there safely!"
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
        return {
            "content": "🔍 Here's what I can do:\n\n" +
                "/connect - Connect or create a wallet\n" +
                "/price [token] - Check token price (e.g., /price ETH)\n" +
                "/swap [amount] [token] for [token] - Create a swap (e.g., /swap 0.1 ETH for USDC)\n" +
                "/balance - Check your wallet balance\n" +
                "/disconnect - Disconnect your wallet\n\n" +
                "I'm still learning, so please be patient with me! 🐌"
        }

    async def _handle_connect_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /connect command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content and optional button markup
        """
        # Check if user already has a wallet
        if wallet_address:
            return {
                "content": f"You already have a wallet connected!\n\n" +
                    f"Address: {wallet_address}\n\n" +
                    f"Use /disconnect if you want to disconnect this wallet."
            }
        
        # Create buttons for wallet options
        buttons = [
            [
                {"text": "Create New Wallet", "callback_data": "create_wallet"},
                {"text": "Connect Existing", "callback_data": "connect_existing"}
            ]
        ]
        
        return {
            "content": "Let's set up your wallet. You can create a new wallet or connect an existing one:",
            "metadata": {
                "telegram_buttons": buttons
            }
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
                "content": "You don't have a wallet connected yet. Use /connect to set up your wallet."
            }
        
        # For MVP, simulate balance data
        balances = self._get_simulated_balance(wallet_address)
        
        return {
            "content": f"Your wallet balance:\n\n" +
                f"ETH: {balances['eth']}\n" +
                f"USDC: {balances['usdc']}\n" +
                f"USDT: {balances['usdt']}\n" +
                f"DAI: {balances['dai']}\n\n" +
                f"Wallet: {wallet_address[:6]}...{wallet_address[-4:]}"
        }

    async def _handle_price_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle the /price command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not args:
            return {
                "content": "Please specify a token. Example: /price ETH"
            }
        
        token = args.split()[0].upper()
        
        # Process via the price check handler
        result = await self._handle_price_check(f"price of {token}", 534352)  # Scroll chain ID
        
        return result

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
        if not wallet_address:
            return {
                "content": "You need to connect a wallet first. Use /connect to set up your wallet."
            }
        
        if not args:
            return {
                "content": "Please specify the swap details. Example: /swap 0.1 ETH for USDC"
            }
        
        # Parse the swap text
        swap_match = re.search(r"(\d+\.?\d*)\s+(\w+)\s+(?:to|for)\s+(\w+)", args, re.I)
        
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
                {"text": "Approve Swap", "callback_data": f"approve_swap:{json.dumps(swap_info)}"},
                {"text": "Cancel", "callback_data": "cancel_swap"}
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
        Handle the /disconnect command.
        
        Args:
            user_id: Telegram user ID
            args: Command arguments
            wallet_address: User's wallet address if already connected
            
        Returns:
            Dict with response content
        """
        if not wallet_address:
            return {
                "content": "You don't have a wallet connected."
            }
        
        return {
            "content": f"Wallet disconnected: {wallet_address[:6]}...{wallet_address[-4:]}",
            "wallet_address": None  # Signal to remove the wallet
        }

    def _generate_wallet_address(self, user_id: str) -> str:
        """
        Generate a deterministic wallet address for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            A simulated Ethereum wallet address
        """
        # TODO: Implement actual smart wallet creation using Account Abstraction
        # For a complete implementation we would:
        # 1. Generate an EOA key for the user (securely)
        # 2. Deploy a smart contract wallet (like Safe or ERC-4337 compatible wallet)
        # 3. Store wallet info securely
        # 4. Use this wallet for actual on-chain operations
        
        # For now, we create a deterministic but random-looking address based on user ID
        seed = f"snel_wallet_{user_id}_{random.randint(1, 1000000)}"
        address_hash = hashlib.sha256(seed.encode()).hexdigest()
        return f"0x{address_hash[:40]}"

    def _get_simulated_balance(self, wallet_address: str) -> Dict[str, float]:
        """
        Get simulated token balances for a wallet.
        
        Args:
            wallet_address: Ethereum wallet address
            
        Returns:
            Dict with token balances
        """
        # Use the wallet address as a seed for deterministic but random-looking balances
        seed = int(wallet_address[2:10], 16)
        random.seed(seed)
        
        return {
            "eth": round(random.uniform(0.1, 2.5), 4),
            "usdc": round(random.uniform(100, 5000), 2),
            "usdt": round(random.uniform(50, 2000), 2),
            "dai": round(random.uniform(75, 3000), 2)
        }

    async def process_message(
        self,
        message: str,
        platform: str,
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a general message and provide a response."""
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
                        "🔹 */help* - See all commands\n\n" +
                        "Try one of these commands to get started! Just tap on a command or type it.\n\n" +
                        "Or ask me something like \"What's the price of Bitcoin?\" or \"Tell me about Scroll L2\"."
                }
            
        # Original implementation continues for other message types
        result = await super().process_message(
            message=message,
            platform=platform,
            user_id=user_id,
            wallet_address=wallet_address,
            metadata=metadata
        )
        
        # If we have a valid wallet address but user is asking about transactions
        # without using commands, guide them to the right format
        transaction_patterns = [
            r"(?:swap|buy|sell|trade|exchange)",
            r"(?:send|transfer)",
            r"(?:bridge)",
        ]
        
        if wallet_address and any(re.search(pattern, message.lower()) for pattern in transaction_patterns):
            if "I'm not sure" in result.get("content", "") or "I don't know" in result.get("content", ""):
                return {
                    "content": "🐌 I noticed you might want to do a transaction. Try using one of these command formats:\n\n" +
                        "For swaps: */swap 0.1 ETH for USDC*\n" +
                        "For transfers: */send 10 USDC to 0xAddress*\n" +
                        "For bridges: */bridge 0.1 ETH from Scroll to Base*\n\n" +
                        "This makes it easier for me to understand exactly what you want to do."
                }
                
        return result 