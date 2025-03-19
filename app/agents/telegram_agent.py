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
from pydantic import Field, BaseModel
from app.agents.messaging_agent import MessagingAgent
from app.services.prices import PriceService
from app.services.token_service import TokenService
from app.services.swap_service import SwapService
from app.services.wallet_bridge_service import WalletBridgeService
from app.services.telegram_service import TelegramService
from app.services.wallet_service import WalletService
from collections import defaultdict
from datetime import datetime, timedelta

# Use a type annotation instead of importing the class
# This breaks the circular import
TelegramMessage = Dict[str, Any]  # Type annotation only

logger = logging.getLogger(__name__)

# Default blockchain network
DEFAULT_CHAIN = "base_sepolia"

# Network mapping for price lookups
NETWORK_MAP = {
    "base": (8453, "Base"),
    "scroll": (534352, "Scroll"),
    "ethereum": (1, "Ethereum"),
    "optimism": (10, "Optimism"),
    "polygon": (137, "Polygon"),
    "arbitrum": (42161, "Arbitrum")
}

class RateLimiter:
    """Simple rate limiter for commands."""
    def __init__(self, max_calls: int = 5, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if the user is allowed to make another call."""
        now = time.time()
        user_calls = self.calls[user_id]
        
        # Remove old calls
        user_calls = [call for call in user_calls if call > now - self.time_window]
        self.calls[user_id] = user_calls
        
        # Check if under limit
        return len(user_calls) < self.max_calls
    
    def add_call(self, user_id: str):
        """Record a call for the user."""
        self.calls[user_id].append(time.time())

class PriceCache:
    """Simple cache for token prices."""
    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached price data if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            del self.cache[key]
        return None
    
    def set(self, key: str, data: Dict):
        """Cache price data with timestamp."""
        self.cache[key] = (data, time.time())

class TelegramAgent(MessagingAgent):
    """
    Agent for handling Telegram-specific interactions.
    
    This agent extends the MessagingAgent with Telegram-specific features
    like commands, wallet creation, and inline buttons.
    """
    command_handlers: Dict[str, Callable] = Field(default_factory=dict)
    wallet_bridge_service: Optional[WalletBridgeService] = None
    telegram_service: Optional[TelegramService] = None
    wallet_service: Optional[WalletService] = None
    gemini_service: Optional[Any] = None
    rate_limiter: RateLimiter = Field(default_factory=lambda: RateLimiter())
    price_cache: PriceCache = Field(default_factory=lambda: PriceCache())
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def __init__(
        self, 
        token_service: TokenService, 
        swap_service: SwapService,
        wallet_service: Optional[WalletService] = None,
        wallet_bridge_service: Optional[WalletBridgeService] = None,
        gemini_service: Optional[Any] = None
    ):
        """Initialize the Telegram agent."""
        super().__init__(token_service, swap_service)
        self.wallet_service = wallet_service
        self.wallet_bridge_service = wallet_bridge_service or WalletBridgeService(redis_url=os.getenv("REDIS_URL"))
        self.telegram_service = TelegramService(wallet_bridge=self.wallet_bridge_service)
        self.gemini_service = gemini_service
        self.rate_limiter = RateLimiter()
        self.price_cache = PriceCache()
        
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
            "network": self._handle_network_command
        }
        
        logger.info("TelegramAgent initialized with commands: %s", list(self.command_handlers.keys()))

    async def process_telegram_update(
        self,
        update: Dict[str, Any],
        user_id: str,
        wallet_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a Telegram update object."""
        logger.info(f"Processing Telegram update for user {user_id}")
        
        # Handle different types of updates
        if "message" in update and "text" in update["message"]:
            message_text = update["message"]["text"]
            logger.info(f"Processing text message: '{message_text}'")
            
            # Handle commands directly if possible for better debugging
            if message_text.startswith("/"):
                # Extract command and arguments
                parts = message_text.split(maxsplit=1)
                command = parts[0][1:]  # Remove the slash
                args = parts[1] if len(parts) > 1 else ""
                
                logger.info(f"Direct command processing: {command} with args: {args}")
                return await self._handle_command(command, args, user_id, wallet_address)
            else:
                # For non-command messages, use Gemini if available
                if self.gemini_service:
                    try:
                        # Add wallet info if available
                        wallet_info = {"wallet_address": wallet_address} if wallet_address else None
                        
                        # Get response from Gemini
                        response = await self.gemini_service.answer_crypto_question(
                            message_text,
                            wallet_info
                        )
                        
                        return {"content": response}
                    except Exception as e:
                        logger.warning(f"Error getting Gemini response: {e}")
                
                # Fallback to help message if Gemini fails or isn't available
                return {
                    "content": "🐌 Hello! I'm Snel, your DeFi assistant. Try these commands:\n\n" +
                              "*/price ETH* - Check ETH price\n" +
                              "*/connect* - Connect your wallet\n" +
                              "*/help* - See all commands"
                }
        else:
            # Default response for unsupported update types
            logger.warning(f"Unsupported update type: {list(update.keys())}")
            return {
                "content": "Sorry, I can only handle text messages. Try /help to see available commands."
            }

    async def _process_text_message(self, message: str, user_id: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Process a text message."""
        # Use Gemini for conversational responses if available
        if self.gemini_service:
            try:
                wallet_info = {"wallet_address": wallet_address} if wallet_address else None
                response = await self.gemini_service.answer_crypto_question(message, wallet_info)
                return {"content": response}
            except Exception as e:
                logger.warning(f"Error getting Gemini response: {e}")
                
        # Fallback to help command if Gemini fails or isn't available
        return await self._handle_help_command(user_id, "", wallet_address)

    async def _handle_help_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the /help command."""
        if wallet_address:
            help_text = (
                "🐌 *Available Commands*\n\n"
                "• `/price [token]` - Check token prices\n"
                "• `/balance` - View your wallet balance\n"
                "• `/swap [amount] [from] for [to]` - Swap tokens\n\n"
                f"Connected wallet: `{wallet_address[:6]}...{wallet_address[-4:]}`"
            )
        else:
            help_text = (
                "🐌 *Welcome to Snel!*\n\n"
                "First step: Connect your wallet with `/connect`\n\n"
                "*Available Commands*\n"
                "• `/price [token]` - Check token prices\n"
                "• `/balance` - View your wallet balance\n"
                "• `/swap [amount] [from] for [to]` - Swap tokens"
            )
        
        return {"content": help_text}

    async def _handle_connect_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the /connect command."""
        if wallet_address:
            return {"content": f"Wallet already connected: `{wallet_address[:6]}...{wallet_address[-4:]}`"}
        
        # Generate connection URL - prefix telegram: to user_id to namespace it
        bridge_url = self.wallet_bridge_service.generate_connect_url(f"telegram:{user_id}")
        
        connect_text = (
            "*Connect Your Wallet*\n\n"
            "1. [Click here to connect]({url})\n"
            "2. Connect with MetaMask or Web3 wallet\n"
            "3. Sign message to verify ownership\n\n"
            "_Your private keys stay secure - this is only to view balances and craft transactions for you to sign there._"
        ).format(url=bridge_url)
        
        return {"content": connect_text}

    async def _handle_balance_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the /balance command."""
        try:
            if not self.wallet_bridge_service:
                return {"content": "Balance check is temporarily unavailable."}
            
            if not wallet_address:
                return {"content": "You need to connect a wallet first. Use /connect to get started."}
            
            balance_result = await self.wallet_bridge_service.get_wallet_balance(user_id, platform="telegram")
            
            if not balance_result.get("success"):
                return {
                    "content": f"Error retrieving balance: {balance_result.get('error')}"
                }
            
            chain_info = balance_result.get("chain_info", {})
            chain_name = chain_info.get("name", "Unknown Network")
            eth_balance = balance_result.get("balance", {}).get("eth", "0")
            tokens = balance_result.get("balance", {}).get("tokens", [])
            
            message_parts = [
                f"💰 **Balance on {chain_name}**\n",
                f"**ETH**: {eth_balance}"
            ]
            
            if tokens:
                message_parts.append("\n**Tokens**:")
                for token in tokens:
                    symbol = token.get("symbol", "???")
                    balance = token.get("balance", "0")
                    message_parts.append(f"• {symbol}: {balance}")
            
            return {"content": "\n".join(message_parts)}
            
        except Exception as e:
            logger.exception(f"Error in balance command: {e}")
            return {"content": "Error checking balance. Please try again later."}

    async def _handle_price_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the /price command with caching."""
        if not args:
            return {"content": "Please specify a token symbol, e.g. `/price ETH`"}
        
        # Parse token and optional network
        parts = args.lower().split(" on ")
        token = parts[0].strip().upper()
        token = re.sub(r'^[$#]', '', token)
        
        # Default to Base chain
        chain_id, chain_name = NETWORK_MAP["base"]
        
        if len(parts) > 1:
            network = parts[1].strip().lower()
            if network not in NETWORK_MAP:
                networks = "\n".join([f"• {name}" for name in NETWORK_MAP.keys()])
                return {
                    "content": f"🤔 I don't support the network '{network}' yet.\n\n"
                              f"Try one of these:\n{networks}"
                }
            chain_id, chain_name = NETWORK_MAP[network]
        
        # Check cache first
        cache_key = f"{token}:{chain_id}"
        cached_data = self.price_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Handle major tokens with 24h changes
            major_tokens = {"ETH", "WETH", "USDC", "USDT", "WBTC", "BTC"}
            show_24h = token in major_tokens
            
            response = None
            if show_24h:
                try:
                    price_service = PriceService()
                    price_data = await price_service.get_token_price(token, chain_id)
                    if price_data and "price" in price_data:
                        price = price_data["price"]
                        change_24h = price_data.get("change_24h", 0)
                        
                        price_str = self._format_price(price)
                        change_str = self._format_change(change_24h)
                        
                        response = {
                            "content": f"💰 *{token} Price*\n"
                                      f"Network: {chain_name}\n"
                                      f"Price: {price_str}\n"
                                      f"24h Change: {change_str}"
                        }
                except Exception as e:
                    logger.warning(f"Failed to get 24h change for {token}, falling back to basic price: {e}")
                    show_24h = False
            
            # Fallback to basic price
            if not response:
                price, decimals = await self.token_service.get_token_price(token, "usd", chain_id)
                if price is not None:
                    price_str = self._format_price(price)
                    response = {
                        "content": f"💰 *{token} Price*\n"
                                  f"Network: {chain_name}\n"
                                  f"Price: {price_str}"
                    }
                else:
                    response = {
                        "content": f"🤔 I couldn't find a price for {token} on {chain_name}.\n\n"
                                  "Try popular tokens like:\n"
                                  "• `ETH`\n"
                                  "• `USDC`\n"
                                  "• `WETH`\n"
                                  "• `WBTC`"
                    }
            
            # Cache successful responses
            if "couldn't find" not in response["content"]:
                self.price_cache.set(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting price for {token}: {e}")
            return {
                "content": "😅 Oops! I had trouble fetching that price.\n"
                          "Make sure you're using the correct token symbol and try again.\n\n"
                          "Example: `/price ETH on base`"
            }
    
    def _format_price(self, price: float) -> str:
        """Format price based on its value."""
        if price >= 100:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        return f"${price:.6f}"
    
    def _format_change(self, change: float) -> str:
        """Format 24h price change with emoji."""
        if change > 0:
            return f"📈 +{change:.2f}%"
        elif change < 0:
            return f"📉 {change:.2f}%"
        return "➡️ 0.00%"

    async def _handle_swap_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the /swap command."""
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
            wallet_data = await self.wallet_bridge_service.get_wallet_info(user_id, platform="telegram")
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
                
                return {
                    "content": f"💱 **Swap Quote (Testnet)**\n\n" +
                        f"From: {amount} {from_token}\n" +
                        f"To: ~{estimated_output} {to_token}\n" +
                        f"Rate: 1 {from_token} = {rate} {to_token}\n" +
                        f"Network: {wallet_chain.replace('_', ' ').title()}\n" +
                        f"Fee: 0.3%\n\n" +
                        "_Note: This is a testnet swap and will use testnet tokens only. No real value will be exchanged._\n\n" +
                        "Use */swap confirm* to proceed with this swap."
                }
            else:
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
        if self.wallet_bridge_service:
            try:
                await self.wallet_bridge_service.delete_wallet(
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
        """Handle the /networks command to show available networks."""
        if not self.wallet_bridge_service:
            networks = [
                {"id": "scroll_sepolia", "name": "Scroll Sepolia", "description": "Scroll L2 testnet"},
                {"id": "base_sepolia", "name": "Base Sepolia", "description": "Base L2 testnet"},
                {"id": "ethereum_sepolia", "name": "Ethereum Sepolia", "description": "Ethereum testnet"}
            ]
        else:
            try:
                networks = await self.wallet_bridge_service.get_supported_chains()
            except Exception as e:
                logger.exception(f"Error getting networks: {e}")
                networks = []
                
        if not networks:
            return {
                "content": "No networks available at the moment. Please try again later."
            }
            
        # Get current network if user has a wallet
        current_network = DEFAULT_CHAIN
        if wallet_address and self.wallet_bridge_service:
            try:
                wallet_info = await self.wallet_bridge_service.get_wallet_info(str(user_id), "telegram")
                if wallet_info and "chain" in wallet_info:
                    current_network = wallet_info["chain"]
            except Exception as e:
                logger.exception(f"Error getting current network: {e}")
        
        # Format network list
        networks_text = "🌐 Available Networks:\n\n"
        
        for network in networks:
            network_id = network["id"]
            network_name = network["name"]
            network_desc = network.get("description", "")
            
            # Mark current network
            current_marker = "✅ " if network_id == current_network else ""
            networks_text += f"{current_marker}**{network_name}** ({network_id})\n{network_desc}\n\n"
        
        # Add instructions
        if wallet_address:
            networks_text += "Switch networks using:\n/network [network_id]"
        else:
            networks_text += "Connect a wallet first with /connect to use these networks."
        
        return {"content": networks_text}

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
        
        if not self.wallet_bridge_service:
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
        result = await self.wallet_bridge_service.switch_chain(
            user_id=str(user_id),
            platform="telegram",
            chain=network_name
        )
        
        if result["success"]:
            return {
                "content": f"🌐 Switched network to {result['chain_info']['name']} successfully!\n\nYou can now use other commands like /swap and /balance on this network."
            }
        else:
            available_chains = await self.wallet_bridge_service.get_supported_chains()
            network_list = ", ".join([chain["id"] for chain in available_chains])
            
            return {
                "content": f"❌ {result['message']}\n\nAvailable networks: {network_list}\n\nUse /networks to see details."
            }

    async def _handle_command(
        self, command: str, args: str, user_id: str, wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle a Telegram command with rate limiting."""
        logger.info(f"Handling command '{command}' with args '{args}' for user {user_id}")
        
        # Skip rate limiting for certain commands
        rate_limited_commands = {'price', 'swap', 'balance'}
        if command in rate_limited_commands:
            if not self.rate_limiter.is_allowed(user_id):
                return {
                    "content": "⚠️ You're making too many requests. Please wait a minute and try again."
                }
            self.rate_limiter.add_call(user_id)
        
        # Check if the command has a handler
        if command in self.command_handlers:
            handler = self.command_handlers[command]
            logger.info(f"Found handler for command '{command}': {handler.__name__}")
            
            # For commands that require a wallet, check if connected
            wallet_required_commands = {'balance', 'swap', 'disconnect', 'network'}
            if command in wallet_required_commands and not wallet_address:
                return await self._handle_connect_command(user_id, args, wallet_address)
            
            # For swap command, require arguments
            if command == 'swap' and not args:
                return {
                    "content": "Please specify the swap details. Example: /swap 0.1 ETH for USDC"
                }
            
            return await handler(user_id, args, wallet_address)
        else:
            # For unknown commands, show help
            return await self._handle_help_command(user_id, "", wallet_address)

    async def _handle_start_command(self, user_id: str, args: str, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """Handle the /start command."""
        return {
            "content": "Hello there! 👋 I'm Snel, i do defi stuff 🐌!\n\n" +
                      "Web3 is my jam, i help you with that, slowly.\n\n" +
                      "Available commands:\n" +
                      "*/price [token]* - Check token prices (e.g. */price ETH on base*)\n" +
                      "*/connect* - Connect your wallet\n" +
                      "*/balance* - Check your balance\n" +
                      "*/swap [amount] [token] for [token]* - Swap tokens\n" +
                      "*/networks* - See available networks\n" +
                      "*/help* - Show all commands"
        } 