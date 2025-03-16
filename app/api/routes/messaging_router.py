from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal
import logging
import json
import httpx
import os
from datetime import datetime

from app.api.dependencies import get_redis_service, get_token_service
from app.agents.agent_factory import get_agent_factory
from app.services.pipeline import Pipeline
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.agents.messaging_agent import MessagingAgent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["messaging"])

# Environment variables for messaging platforms
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

class WhatsAppMessage(BaseModel):
    """WhatsApp message webhook payload."""
    object: str
    entry: List[Dict[str, Any]]

class TelegramMessage(BaseModel):
    """Telegram message webhook payload."""
    update_id: int
    message: Dict[str, Any]

class MessagingRequest(BaseModel):
    """Generic messaging request for testing."""
    platform: Literal["whatsapp", "telegram"]
    user_id: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class MessagingResponse(BaseModel):
    """Response to a messaging request."""
    content: str
    platform: str
    user_id: Optional[str] = None
    wallet_address: Optional[str] = None
    awaiting_confirmation: bool = False
    metadata: Optional[Dict[str, Any]] = None

async def get_messaging_agent(
    redis_service: RedisService = Depends(get_redis_service),
    token_service: TokenService = Depends(get_token_service),
    agent_factory = Depends(get_agent_factory)
) -> MessagingAgent:
    """Get an instance of MessagingAgent."""
    # Create a pipeline for the messaging agent
    pipeline = Pipeline(
        token_service=token_service,
        swap_agent=agent_factory.create_agent("swap"),
        price_agent=agent_factory.create_agent("price"),
        dca_agent=agent_factory.create_agent("dca"),
        redis_service=redis_service
    )
    
    # Create and return the messaging agent
    return MessagingAgent(
        token_service=token_service,
        redis_service=redis_service,
        pipeline=pipeline
    )

@router.post("/whatsapp/webhook", response_model=Dict[str, Any])
async def whatsapp_webhook(
    message: WhatsAppMessage,
    background_tasks: BackgroundTasks,
    messaging_agent: MessagingAgent = Depends(get_messaging_agent),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Handle WhatsApp webhook messages.
    
    This endpoint receives messages from the WhatsApp Business API
    and processes them using the messaging agent.
    """
    try:
        logger.info(f"Received WhatsApp webhook: {message.object}")
        
        # Verify this is a WhatsApp message
        if message.object != "whatsapp_business_account":
            logger.warning(f"Unexpected object type: {message.object}")
            return {"status": "ignored"}
        
        # Process each entry
        for entry in message.entry:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                for msg in messages:
                    # Extract message details
                    msg_type = msg.get("type")
                    if msg_type != "text":
                        # Only handle text messages for now
                        continue
                    
                    from_user = msg.get("from", "")
                    text = msg.get("text", {}).get("body", "")
                    
                    # Process in background to avoid webhook timeout
                    background_tasks.add_task(
                        process_whatsapp_message,
                        from_user=from_user,
                        text=text,
                        messaging_agent=messaging_agent,
                        redis_service=redis_service
                    )
        
        # Return 200 OK to acknowledge receipt
        return {"status": "processing"}
        
    except Exception as e:
        logger.exception(f"Error processing WhatsApp webhook: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/telegram/webhook", response_model=Dict[str, Any])
async def telegram_webhook(
    update: TelegramMessage,
    background_tasks: BackgroundTasks,
    messaging_agent: MessagingAgent = Depends(get_messaging_agent),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Handle Telegram webhook messages.
    
    This endpoint receives messages from the Telegram Bot API
    and processes them using the messaging agent.
    """
    try:
        logger.info(f"Received Telegram webhook: {update.update_id}")
        
        # Extract message details
        chat_id = update.message.get("chat", {}).get("id")
        text = update.message.get("text", "")
        
        if not chat_id or not text:
            logger.warning("Missing chat_id or text in Telegram message")
            return {"status": "ignored"}
        
        # Process in background to avoid webhook timeout
        background_tasks.add_task(
            process_telegram_message,
            chat_id=str(chat_id),
            text=text,
            messaging_agent=messaging_agent,
            redis_service=redis_service
        )
        
        # Return 200 OK to acknowledge receipt
        return {"status": "processing"}
        
    except Exception as e:
        logger.exception(f"Error processing Telegram webhook: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/test", response_model=MessagingResponse)
async def test_messaging(
    request: MessagingRequest,
    messaging_agent: MessagingAgent = Depends(get_messaging_agent),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Test endpoint for messaging integration.
    
    This endpoint allows testing the messaging agent without
    setting up actual WhatsApp or Telegram webhooks.
    """
    try:
        # Check if user has a linked wallet
        wallet_address = None
        if redis_service:
            key = f"messaging:{request.platform}:user:{request.user_id}:wallet"
            wallet_address = await redis_service.get(key)
        
        # Process the message
        result = await messaging_agent.process_message(
            message=request.message,
            platform=request.platform,
            user_id=request.user_id,
            wallet_address=wallet_address,
            metadata=request.metadata
        )
        
        # Return the response
        return MessagingResponse(
            content=result.get("content", "No response"),
            platform=request.platform,
            user_id=request.user_id,
            wallet_address=result.get("wallet_address", wallet_address),
            awaiting_confirmation=result.get("awaiting_confirmation", False),
            metadata=result.get("metadata")
        )
        
    except Exception as e:
        logger.exception(f"Error in test messaging: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get("/linked-wallets/{platform}/{user_id}")
async def get_linked_wallet(
    platform: str,
    user_id: str,
    redis_service: RedisService = Depends(get_redis_service)
):
    """Get the linked wallet for a messaging platform user."""
    try:
        key = f"messaging:{platform}:user:{user_id}:wallet"
        wallet_address = await redis_service.get(key)
        
        if not wallet_address:
            return {"linked": False}
        
        return {
            "linked": True,
            "wallet_address": wallet_address
        }
        
    except Exception as e:
        logger.exception(f"Error getting linked wallet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get linked wallet: {str(e)}"
        )

@router.delete("/unlink-wallet/{platform}/{user_id}")
async def unlink_wallet(
    platform: str,
    user_id: str,
    redis_service: RedisService = Depends(get_redis_service)
):
    """Unlink a wallet from a messaging platform user."""
    try:
        key = f"messaging:{platform}:user:{user_id}:wallet"
        wallet_address = await redis_service.get(key)
        
        if not wallet_address:
            return {"success": True, "message": "No wallet linked"}
        
        # Delete the mapping
        await redis_service.delete(key)
        
        # Also delete the reverse mapping
        reverse_key = f"wallet:{wallet_address}:{platform}:user"
        await redis_service.delete(reverse_key)
        
        return {
            "success": True,
            "message": f"Wallet {wallet_address[:6]}...{wallet_address[-4:]} unlinked successfully"
        }
        
    except Exception as e:
        logger.exception(f"Error unlinking wallet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unlink wallet: {str(e)}"
        )

async def process_whatsapp_message(
    from_user: str,
    text: str,
    messaging_agent: MessagingAgent,
    redis_service: RedisService
):
    """Process a WhatsApp message in the background."""
    try:
        logger.info(f"Processing WhatsApp message from {from_user}: {text}")
        
        # Check if user has a linked wallet
        wallet_address = None
        if redis_service:
            key = f"messaging:whatsapp:user:{from_user}:wallet"
            wallet_address = await redis_service.get(key)
        
        # Process the message
        result = await messaging_agent.process_message(
            message=text,
            platform="whatsapp",
            user_id=from_user,
            wallet_address=wallet_address
        )
        
        # Send the response back to WhatsApp
        await send_whatsapp_message(
            to=from_user,
            message=result.get("content", "No response")
        )
        
    except Exception as e:
        logger.exception(f"Error processing WhatsApp message: {e}")
        # Try to send error message
        try:
            await send_whatsapp_message(
                to=from_user,
                message=f"Sorry, an error occurred: {str(e)}"
            )
        except:
            pass

async def process_telegram_message(
    chat_id: str,
    text: str,
    messaging_agent: MessagingAgent,
    redis_service: RedisService
):
    """Process a Telegram message in the background."""
    try:
        logger.info(f"Processing Telegram message from {chat_id}: {text}")
        
        # Check if user has a linked wallet
        wallet_address = None
        if redis_service:
            key = f"messaging:telegram:user:{chat_id}:wallet"
            wallet_address = await redis_service.get(key)
        
        # Process the message
        result = await messaging_agent.process_message(
            message=text,
            platform="telegram",
            user_id=chat_id,
            wallet_address=wallet_address
        )
        
        # Send the response back to Telegram
        await send_telegram_message(
            chat_id=chat_id,
            message=result.get("content", "No response")
        )
        
    except Exception as e:
        logger.exception(f"Error processing Telegram message: {e}")
        # Try to send error message
        try:
            await send_telegram_message(
                chat_id=chat_id,
                message=f"Sorry, an error occurred: {str(e)}"
            )
        except:
            pass

async def send_whatsapp_message(to: str, message: str):
    """Send a message via WhatsApp Business API."""
    if not WHATSAPP_API_KEY:
        logger.warning("WhatsApp API key not configured")
        return
    
    try:
        # This is a placeholder for the actual WhatsApp API call
        # You would need to implement this based on your WhatsApp Business API provider
        # (e.g., Twilio, MessageBird, etc.)
        logger.info(f"Would send WhatsApp message to {to}: {message}")
        
        # Example implementation for Meta WhatsApp Business API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://graph.facebook.com/v17.0/FROM_PHONE_ID/messages",
                headers={
                    "Authorization": f"Bearer {WHATSAPP_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {
                        "body": message
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"WhatsApp API error: {response.text}")
            
    except Exception as e:
        logger.exception(f"Error sending WhatsApp message: {e}")

async def send_telegram_message(chat_id: str, message: str):
    """Send a message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return
    
    try:
        # Send message via Telegram Bot API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Telegram API error: {response.text}")
            
    except Exception as e:
        logger.exception(f"Error sending Telegram message: {e}")
