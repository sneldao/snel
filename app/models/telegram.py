from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class TelegramMessage(BaseModel):
    """
    Model for Telegram webhook request data.
    
    This represents the data structure sent by Telegram when a webhook is triggered.
    """
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None
    inline_query: Optional[Dict[str, Any]] = None
    chosen_inline_result: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None
    shipping_query: Optional[Dict[str, Any]] = None
    pre_checkout_query: Optional[Dict[str, Any]] = None
    poll: Optional[Dict[str, Any]] = None
    poll_answer: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic model configuration."""
        extra = "allow"  # Allow extra fields for forward compatibility
        
# For backward compatibility
TelegramWebhookRequest = TelegramMessage 