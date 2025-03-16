"""
Messaging agent for WhatsApp and Telegram integration.
"""
import logging
import json
from typing import Dict, Any, List, Optional, Union
from app.agents.base import PointlessAgent
from app.services.token_service import TokenService
from app.services.prices import price_service
from app.services.swap_service import SwapService
from app.services.transaction_executor import transaction_executor

logger = logging.getLogger(__name__)

class MessagingAgent(PointlessAgent):
    """
    Agent for handling messaging platform interactions (WhatsApp/Telegram).
    
    This agent processes commands from messaging platforms and returns
    appropriate responses that can be sent back to the user.
    """
    
    def __init__(self, token_service: TokenService, swap_service: SwapService):
        """
        Initialize the messaging agent.
        
        Args:
            token_service: Service for token lookups
            swap_service: Service for swap operations
        """
        self.token_service = token_service
        self.swap_service = swap_service
        
    async def process_message(
        self, 
        message: str, 
        platform: str, 
        user_id: str,
        wallet_address: Optional[str] = None,
        chain_id: int = 534352  # Default to Scroll chain
    ) -> Dict[str, Any]:
        """
        Process a message from a messaging platform.
        
        Args:
            message: The message text
            platform: The platform (whatsapp or telegram)
            user_id: The user ID on the platform
            wallet_address: Optional wallet address
            chain_id: Chain ID (default: Scroll)
            
        Returns:
            Response to send back to the user
        """
        try:
            # Check if this is a wallet connection request
            if "connect wallet" in message.lower():
                return self._handle_connect_wallet(platform, user_id)
                
            # Check if this is a balance check request
            if "balance" in message.lower() or "check balance" in message.lower():
                if not wallet_address:
                    return {
                        "text": "Please connect your wallet first by sending 'connect wallet'",
                        "requires_wallet": True
                    }
                return await self._handle_balance_check(wallet_address, chain_id)
                
            # Check if this is a swap request
            if "swap" in message.lower():
                if not wallet_address:
                    return {
                        "text": "Please connect your wallet first by sending 'connect wallet'",
                        "requires_wallet": True
                    }
                return await self._handle_swap_request(message, wallet_address, chain_id)
                
            # Check if this is a price check request
            if "price" in message.lower() or "how much is" in message.lower():
                return await self._handle_price_check(message, chain_id)
                
            # Default response for unknown commands
            return {
                "text": "I can help you with the following commands:\n\n"
                        "- Connect wallet\n"
                        "- Check balance\n"
                        "- Swap [amount] [token] for [token]\n"
                        "- Price of [token]"
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "text": f"Sorry, I encountered an error: {str(e)}"
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
            "text": "To connect your wallet, please visit the following link:\n\n"
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
                "text": response_text,
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
                "text": f"Sorry, I couldn't check your balance: {str(e)}"
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
                    "text": "Sorry, I couldn't find any quotes for this swap. Please try a different amount or token pair."
                }
            
            # Get the best quote
            best_quote = quotes["quotes"][0] if quotes["quotes"] else None
            
            if not best_quote:
                return {
                    "text": "Sorry, I couldn't find any quotes for this swap. Please try a different amount or token pair."
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
                "text": response_text,
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
                "text": f"Sorry, I couldn't process your swap request: {str(e)}"
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
            # Extract the token from the message
            tokens = ["ETH", "USDC", "USDT", "DAI", "WBTC"]
            token = None
            
            for t in tokens:
                if t.lower() in message.lower():
                    token = t
                    break
            
            if not token:
                return {
                    "text": "Please specify a token to check the price of. For example: 'price of ETH'"
                }
            
            # Get the price of the token
            price_data = await price_service.get_token_price(token, "usd", chain_id)
            price = price_data[0] if price_data and price_data[0] else 0
            
            if price <= 0:
                return {
                    "text": f"Sorry, I couldn't find the price of {token}."
                }
            
            # Format the response
            response_text = f"Current price of {token}:\n\n"
            response_text += f"${price:.2f} USD"
            
            return {
                "text": response_text,
                "price": {
                    "token": token,
                    "usd": price
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking price: {str(e)}")
            return {
                "text": f"Sorry, I couldn't check the price: {str(e)}"
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
