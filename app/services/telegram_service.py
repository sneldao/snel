"""
Service for interacting with the Telegram API.
"""
import logging
import os
import json
import httpx
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from telegram import Update
from telegram.ext import ContextTypes

from app.services.wallet_bridge_service import WalletBridgeService

logger = logging.getLogger(__name__)

# Get Telegram bot token from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Rate limiting for Telegram API to prevent "Too Many Requests" errors
_telegram_rate_limit = {
    "last_request_time": 0,
    "min_interval": 0.05  # 50ms between requests (20 per second)
}

class TelegramService:
    def __init__(self, wallet_bridge: WalletBridgeService):
        self.wallet_bridge = wallet_bridge

    async def handle_transaction_request(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        transaction_data: Dict[str, Any],
        transaction_type: str = "transaction"
    ):
        """Handle a transaction request from a user."""
        try:
            # Create transaction request
            result = await self.wallet_bridge.create_transaction_request(
                user_id=str(update.effective_user.id),
                platform="telegram",
                transaction_data=transaction_data,
                transaction_type=transaction_type
            )
            
            if not result["success"]:
                await update.message.reply_text(
                    "Sorry, there was an error creating your transaction request. "
                    f"Error: {result['error']}"
                )
                return
                
            # Format message with transaction details and URL
            tx_data = {
                "type": transaction_type,
                "data": transaction_data
            }
            message = self.wallet_bridge.format_transaction_message(tx_data)
            message += f"\n\nSign your transaction here: {result['bridge_url']}"
            
            # Send message with URL
            await update.message.reply_text(
                message,
                parse_mode="Markdown"
            )
            
            # Store transaction ID in user data for status updates
            if not context.user_data.get("pending_transactions"):
                context.user_data["pending_transactions"] = []
            context.user_data["pending_transactions"].append(result["transaction_id"])
            
        except Exception as e:
            logger.exception("Error handling transaction request")
            await update.message.reply_text(
                "Sorry, there was an error processing your transaction request. "
                "Please try again later."
            )

    async def check_transaction_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        tx_id: str
    ):
        """Check the status of a transaction."""
        try:
            result = await self.wallet_bridge.get_transaction_status(tx_id)
            
            if not result["success"]:
                await update.message.reply_text(
                    f"Transaction not found: {tx_id}"
                )
                return
                
            tx_data = result["data"]
            status = tx_data["status"]
            
            if status == "completed":
                # Transaction was successful
                tx_result = tx_data.get("result", {})
                if tx_data["type"] == "transaction":
                    await update.message.reply_text(
                        f"✅ Transaction completed!\n\n"
                        f"Transaction hash: `{tx_result.get('transactionHash', 'Unknown')}`",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Message signed!\n\n"
                        f"Signature: `{tx_result.get('signature', 'Unknown')}`",
                        parse_mode="Markdown"
                    )
                    
            elif status == "failed":
                # Transaction failed
                error = tx_data.get("result", {}).get("error", "Unknown error")
                await update.message.reply_text(
                    f"❌ Transaction failed: {error}"
                )
                
            else:
                # Transaction still pending
                await update.message.reply_text(
                    "⏳ Transaction is still pending. Please check back later."
                )
                
        except Exception as e:
            logger.exception("Error checking transaction status")
            await update.message.reply_text(
                "Sorry, there was an error checking your transaction status. "
                "Please try again later."
            )

    async def handle_command_transfer(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        amount: float,
        to_address: str
    ):
        """Handle the /transfer command.
        
        Args:
            update: Telegram update
            context: Bot context
            amount: Amount in ETH to transfer
            to_address: Recipient address
        """
        # Create transaction data
        transaction_data = {
            "to": to_address,
            "value": str(int(amount * 10**18)),  # Convert ETH to Wei
            "data": "0x"  # No contract data for simple transfers
        }
        
        await self.handle_transaction_request(
            update,
            context,
            transaction_data,
            "transaction"
        )
        
    async def handle_command_approve(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        token_address: str,
        spender_address: str,
        amount: int
    ):
        """Handle the /approve command.
        
        Args:
            update: Telegram update
            context: Bot context
            token_address: Token contract address
            spender_address: Address to approve
            amount: Amount to approve
        """
        # Create transaction data for ERC20 approve
        transaction_data = {
            "to": token_address,
            "data": f"0x095ea7b3{spender_address[2:].zfill(64)}{hex(amount)[2:].zfill(64)}",  # approve(address,uint256)
            "value": "0x0"
        }
        
        await self.handle_transaction_request(
            update,
            context,
            transaction_data,
            "transaction"
        )
        
    async def handle_command_sign(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        domain: Dict[str, Any],
        types: Dict[str, Any],
        message: Dict[str, Any]
    ):
        """Handle the /sign command for EIP-712 typed data signing.
        
        Args:
            update: Telegram update
            context: Bot context
            domain: EIP-712 domain
            types: Type definitions
            message: Message to sign
        """
        transaction_data = {
            "domain": domain,
            "types": types,
            "message": message
        }
        
        await self.handle_transaction_request(
            update,
            context,
            transaction_data,
            "signature"
        )

async def send_telegram_message_with_buttons(chat_id: str, message: str, buttons=None, retries=2):
    """Send a message to a Telegram chat."""
    try:
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - _telegram_rate_limit["last_request_time"]
        if time_since_last < _telegram_rate_limit["min_interval"]:
            await asyncio.sleep(_telegram_rate_limit["min_interval"] - time_since_last)
        _telegram_rate_limit["last_request_time"] = current_time
        
        # Prepare request data
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        # Send request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json=data
            )
            
        if response.status_code != 200:
            logger.error(f"Error sending Telegram message: {response.text}")
            if retries > 0:
                await asyncio.sleep(1)
                return await send_telegram_message_with_buttons(chat_id, message, None, retries - 1)
            return None
            
        return response.json()
        
    except Exception as e:
        logger.exception("Error sending Telegram message")
        if retries > 0:
            await asyncio.sleep(1)
            return await send_telegram_message_with_buttons(chat_id, message, None, retries - 1)
        return None 