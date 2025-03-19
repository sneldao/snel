from typing import Optional, Dict, Any
import logging
from app.agents.telegram_agent import TelegramAgent

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, telegram_agent: TelegramAgent):
        """Initialize the bot with a telegram agent."""
        self.telegram_agent = telegram_agent

    async def handle_message(self, update: dict) -> Optional[Dict[str, Any]]:
        """Parse a message update and route to the agent.
        
        Args:
            update: Telegram update object
            
        Returns:
            Optional response data
        """
        # Extract user info
        user_id = None
        if "message" in update:
            user_id = str(update["message"].get("from", {}).get("id", "unknown"))
        elif "callback_query" in update:
            user_id = str(update["callback_query"].get("from", {}).get("id", "unknown"))
            
        if not user_id:
            logger.warning(f"Ignoring update without user_id: {update}")
            return None
            
        # Get wallet info if available
        wallet_address = None
        if self.telegram_agent.wallet_bridge_service:
            try:
                wallet_info = await self.telegram_agent.wallet_bridge_service.get_wallet_info(
                    user_id=user_id,
                    platform="telegram"
                )
                if wallet_info and wallet_info.get("success"):
                    wallet_address = wallet_info.get("wallet_address")
            except Exception as e:
                logger.warning(f"Error getting wallet info: {e}")

        # Process through the agent
        return await self.telegram_agent.process_telegram_update(
            update=update,
            user_id=user_id,
            wallet_address=wallet_address
        ) 