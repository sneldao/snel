from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal, TYPE_CHECKING
import logging
import json
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv
import sys
import uuid
import time
import asyncio

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local", override=True)  # Override with .env.local if it exists

from app.api.dependencies import get_redis_service, get_token_service, get_wallet_service, get_wallet_service_factory, get_gemini_service, get_wallet_bridge_service
from app.agents.agent_factory import get_agent_factory
from app.services.pipeline import Pipeline
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.agents.messaging_agent import MessagingAgent
from app.services.swap_service import SwapService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.services.gemini_service import GeminiService
from app.services.telegram_service import send_telegram_message_with_buttons
from app.services.wallet_bridge_service import WalletBridgeService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["messaging"], prefix="")

# Environment variables for messaging platforms
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
logger.info(f"Loaded TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}... from environment")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# Global cache for services
_service_cache = {}

# Rate limiting for Telegram API to prevent "Too Many Requests" errors
_telegram_rate_limit = {
    "last_request_time": 0,
    "min_interval": 0.05  # 50ms between requests (20 per second)
}

class WhatsAppMessage(BaseModel):
    """WhatsApp message webhook payload."""
    object: str
    entry: List[Dict[str, Any]]

class TelegramMessage(BaseModel):
    """Telegram message webhook payload."""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None

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

class TokenConfig(BaseModel):
    """Token configuration for messaging platforms."""
    token: str

async def get_messaging_agent(
    redis_service: RedisService = Depends(get_redis_service),
    token_service: TokenService = Depends(get_token_service)
) -> MessagingAgent:
    """Get an instance of MessagingAgent."""
    # Create a simple swap agent for the swap service
    swap_agent = SimpleSwapAgent()
    
    # Create a swap service for the messaging agent
    swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
    
    # Create and return the messaging agent
    return MessagingAgent(
        token_service=token_service,
        swap_service=swap_service
    )

async def get_telegram_agent(
    redis_service: RedisService = Depends(get_redis_service),
    token_service: TokenService = Depends(get_token_service),
    wallet_bridge_service: WalletBridgeService = Depends(get_wallet_bridge_service),
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> Any:
    """Get an instance of TelegramAgent."""
    # Check if we already have an instance in the cache
    cache_key = 'telegram_agent'
    if cache_key in _service_cache:
        # Return the cached instance
        return _service_cache[cache_key]
    
    # Import TelegramAgent here to prevent circular imports
    from app.agents.telegram_agent import TelegramAgent
    
    # Create a simple swap agent for the swap service
    swap_agent = SimpleSwapAgent()
    
    # Create a swap service for the telegram agent
    swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
    
    # Create and return the telegram agent
    agent = TelegramAgent(
        token_service=token_service,
        swap_service=swap_service,
        wallet_bridge_service=wallet_bridge_service
    )
    
    # Add gemini_service as an attribute for conversational responses
    if gemini_service:
        agent.gemini_service = gemini_service
    
    # Cache the instance
    _service_cache[cache_key] = agent
    logger.info("Created and cached TelegramAgent instance")
    
    return agent

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
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Telegram webhook messages.
    
    This endpoint receives messages from the Telegram Bot API
    and processes them using the Telegram agent.
    """
    try:
        # Get the raw request body for debugging
        body = await request.json()
        update_id = body.get('update_id', 'unknown')
        logger.info(f"Received Telegram webhook: {update_id}")
        
        # Add detailed logging
        message = body.get('message', {})
        callback_query = body.get('callback_query', {})
        
        if message:
            user_id = message.get('from', {}).get('id', 'unknown')
            text = message.get('text', '')
            logger.info(f"Telegram message from user {user_id}: '{text}'")
        elif callback_query:
            user_id = callback_query.get('from', {}).get('id', 'unknown')
            data = callback_query.get('data', '')
            logger.info(f"Telegram callback from user {user_id}: '{data}'")
        else:
            logger.warning(f"Unknown update type in Telegram webhook: {list(body.keys())}")
        
        # Process in background to avoid timeouts
        background_tasks.add_task(process_telegram_webhook, body)
        
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
        
        # If there's a wallet address in the result, store it
        if result.get("wallet_address") and result.get("wallet_address") != wallet_address:
            await redis_service.set(
                key=f"messaging:whatsapp:user:{from_user}:wallet",
                value=result["wallet_address"]
            )
            # Also store the reverse mapping
            await redis_service.set(
                key=f"wallet:{result['wallet_address']}:whatsapp:user",
                value=from_user
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

async def process_telegram_webhook(update_dict: Dict[str, Any]):
    """Process a Telegram webhook update."""
    try:
        update_id = update_dict.get('update_id', 'unknown')
        logger.info(f"Processing Telegram webhook: {update_id}")
        
        # Initialize services
        redis_service = await get_redis_service()
        token_service = await get_token_service()
        wallet_bridge_service = await get_wallet_bridge_service()
        logger.info("Initializing WalletBridgeService for Telegram webhook")
        
        # Initialize Telegram agent
        telegram_agent = await get_telegram_agent(
            redis_service=redis_service,
            token_service=token_service,
            wallet_bridge_service=wallet_bridge_service,
            gemini_service=await get_gemini_service()
        )
        logger.info("Successfully created TelegramAgent for webhook")
        
        # Extract message data
        message = update_dict.get('message', {})
        if not message:
            logger.warning("No message found in update")
            return
            
        # Get user ID and message text
        user_id = str(message.get('from', {}).get('id'))
        text = message.get('text', '')
        
        if not user_id or not text:
            logger.warning("Missing user_id or text in message")
            return
            
        logger.info(f"Telegram message from user {user_id}: '{text}'")
        
        # Get user's wallet address if connected
        wallet_address = None
        if wallet_bridge_service:
            try:
                wallet_info = await wallet_bridge_service.get_wallet_info(user_id, platform="telegram")
                if wallet_info and "address" in wallet_info:
                    wallet_address = wallet_info["address"]
            except Exception as e:
                logger.warning(f"Error getting wallet info: {e}")
        
        # Process the message
        response = await telegram_agent.process_telegram_update(
            update=update_dict,
            user_id=user_id,
            wallet_address=wallet_address
        )
        
        if response:
            # Send the response
            content = response.get("content", "")
            if content:
                logger.info(f"Sending Telegram message to {user_id} (length: {len(content)})")
                await send_telegram_message_with_buttons(
                    chat_id=user_id,
                    message=content
                )
                
        logger.info(f"Successfully processed Telegram update for user {user_id}")
        
    except Exception as e:
        logger.exception(f"Error processing Telegram webhook: {e}")
        # Don't raise the exception - we want to acknowledge receipt even if processing fails

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
    global TELEGRAM_BOT_TOKEN

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured, attempting to reload from environment")
        reload_environment_variables()
        if not TELEGRAM_BOT_TOKEN:
            logger.error("Failed to load Telegram bot token from environment")
        return

    try:
        # Log the token (first few characters) for debugging
        token_preview = (
            f"{TELEGRAM_BOT_TOKEN[:5]}..." if TELEGRAM_BOT_TOKEN else "None"
        )
        logger.info(f"Sending Telegram message to {chat_id} using token: {token_preview}")

        # Send message via Telegram Bot API
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            logger.info(f"Sending request to: {url}")

            # Use plain text for simplicity
            payload = {
                    "chat_id": chat_id,
                "text": message
            }

            response = await client.post(url, json=payload)

            if response.status_code != 200:
                logger.error(f"Telegram API error: {response.text}")
                logger.error(f"Request payload: {payload}")

                # If unauthorized, try reloading environment variables
                if "Unauthorized" in response.text:
                    logger.warning("Unauthorized error, attempting to reload environment variables")
                    reload_environment_variables()

                    # Try again with the new token
                    if TELEGRAM_BOT_TOKEN:
                        logger.info(f"Retrying with new token: {TELEGRAM_BOT_TOKEN[:5]}...")
                        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        retry_response = await client.post(url, json=payload)

                        if retry_response.status_code == 200:
                            logger.info(f"Successfully sent message to Telegram chat {chat_id} after token reload")
                            return
                        else:
                            logger.error(f"Telegram API error after token reload: {retry_response.text}")
            else:
                logger.info(f"Successfully sent message to Telegram chat {chat_id}")

    except Exception as e:
        logger.exception(f"Error sending Telegram message: {e}")

@router.get("/telegram/verify-token")
async def verify_telegram_token():
    """Verify that the Telegram bot token is configured and valid."""
    if not TELEGRAM_BOT_TOKEN:
        return {
            "status": "error",
            "message": "Telegram bot token not configured"
        }
    
    try:
        # Check if the token is valid by getting bot info
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Invalid Telegram bot token: {response.text}"
                }
            
            bot_info = response.json()
            return {
                "status": "ok",
                "bot_info": bot_info["result"]
            }
            
    except Exception as e:
        logger.exception(f"Error verifying Telegram token: {e}")
        return {
            "status": "error",
            "message": f"Error verifying token: {str(e)}"
        }

@router.post("/telegram/set-token")
async def set_telegram_token(config: TokenConfig):
    """Set the Telegram bot token dynamically."""
    global TELEGRAM_BOT_TOKEN
    
    try:
        # Verify the token is valid
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.telegram.org/bot{config.token}/getMe")
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Invalid Telegram bot token: {response.text}"
                }
            
            # Set the token
            TELEGRAM_BOT_TOKEN = config.token
            
            # Get bot info
            bot_info = response.json()
            return {
                "status": "ok",
                "message": "Telegram bot token set successfully",
                "bot_info": bot_info["result"]
            }
            
    except Exception as e:
        logger.exception(f"Error setting Telegram token: {e}")
        return {
            "status": "error",
            "message": f"Error setting token: {str(e)}"
        }

@router.get("/env-check")
async def check_environment_variables():
    """Check the environment variables for debugging."""
    # Only show the first few characters of sensitive values
    return {
        "telegram_bot_token": f"{TELEGRAM_BOT_TOKEN[:5]}..." if TELEGRAM_BOT_TOKEN else "Not set",
        "whatsapp_api_key": f"{WHATSAPP_API_KEY[:5]}..." if WHATSAPP_API_KEY else "Not set",
        "webhook_secret": f"{WEBHOOK_SECRET[:5]}..." if WEBHOOK_SECRET else "Not set",
        "env_file_path": os.path.abspath(".env"),
        "env_local_file_path": os.path.abspath(".env.local"),
        "current_directory": os.getcwd(),
    }

def reload_environment_variables():
    """Reload environment variables from .env files."""
    global TELEGRAM_BOT_TOKEN, WHATSAPP_API_KEY, WEBHOOK_SECRET
    
    # Load environment variables from .env files
    load_dotenv()
    load_dotenv(".env.local", override=True)  # Override with .env.local if it exists
    
    # Update global variables
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
    
    logger.info(f"Reloaded environment variables. TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}...")
    
    return {
        "telegram_bot_token": f"{TELEGRAM_BOT_TOKEN[:5]}..." if TELEGRAM_BOT_TOKEN else "Not set",
        "whatsapp_api_key": f"{WHATSAPP_API_KEY[:5]}..." if WHATSAPP_API_KEY else "Not set",
        "webhook_secret": f"{WEBHOOK_SECRET[:5]}..." if WEBHOOK_SECRET else "Not set"
    }

@router.post("/reload-env")
async def reload_env():
    """Reload environment variables from .env files."""
    return reload_environment_variables()

@router.post("/telegram/process", response_model=Dict[str, Any])
async def process_telegram_request(
    request: MessagingRequest,
    telegram_agent: Any = Depends(get_telegram_agent),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Process a Telegram message from the dedicated Telegram bot.
    
    This endpoint is separate from the webhook to isolate the bot functionality
    from the web interface.
    """
    start_time = time.time()
    try:
        # Check if this is coming from our Telegram bot
        metadata = request.metadata or {}
        is_from_bot = metadata.get("source") == "telegram_bot"
        
        # Limit the amount of logging for performance
        logger.info(f"Processing Telegram request from {'bot' if is_from_bot else 'webhook'} for user {request.user_id}")
        
        # Check if user has a linked wallet
        wallet_address = None
        if redis_service:
            try:
                key = f"messaging:telegram:user:{request.user_id}:wallet"
                wallet_address = await redis_service.get(key)
            except Exception as redis_error:
                logger.warning(f"Error fetching wallet: {redis_error}")
        
        # Process the message using the Telegram agent with timeout protection
        try:
            # Create a task with a timeout
            process_task = asyncio.create_task(
                telegram_agent._process_telegram_message(
                    message=request.message,
                    user_id=request.user_id,
                    wallet_address=wallet_address,
                    metadata=request.metadata
                )
            )
            
            # Wait for the task with a timeout (10 seconds)
            result = await asyncio.wait_for(process_task, timeout=10.0)
        except asyncio.TimeoutError:
            logger.error(f"Timeout processing Telegram message for user {request.user_id}")
            return {
                "content": "Sorry, it's taking too long to process your request. Please try again later.",
                "error": "Request timed out"
            }
        
        # If there's a wallet address in the result, store it
        if result.get("wallet_address") is not None:
            try:
                if result.get("wallet_address"):  # Non-empty wallet address
                    await redis_service.set(
                        key=f"messaging:telegram:user:{request.user_id}:wallet",
                        value=result["wallet_address"]
                    )
                    # Also store the reverse mapping
                    await redis_service.set(
                        key=f"wallet:{result['wallet_address']}:telegram:user",
                        value=request.user_id
                    )
                else:  # Empty wallet address = disconnect wallet
                    # Delete the mappings
                    old_wallet = await redis_service.get(f"messaging:telegram:user:{request.user_id}:wallet")
                    if old_wallet:
                        await redis_service.delete(f"wallet:{old_wallet}:telegram:user")
                    await redis_service.delete(f"messaging:telegram:user:{request.user_id}:wallet")
            except Exception as redis_error:
                logger.warning(f"Error updating wallet mappings: {redis_error}")
        
        # Add a flag for the bot to identify this response
        if is_from_bot:
            if not result.get("metadata"):
                result["metadata"] = {}
            result["metadata"]["telegram_bot_response"] = True
            result["metadata"]["processing_time"] = f"{time.time() - start_time:.3f}s"
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"Error processing Telegram request (after {processing_time:.3f}s): {e}")
        
        # Return an appropriate error message based on the exception type
        error_message = "Sorry, I encountered an error."
        if isinstance(e, ValueError):
            error_message = f"Invalid input: {str(e)}"
        elif isinstance(e, KeyError):
            error_message = "Missing required information."
        elif isinstance(e, TimeoutError) or isinstance(e, asyncio.TimeoutError):
            error_message = "Request timed out. Please try again later."
        else:
            error_message = "Sorry, I encountered an unexpected error. Try again later."
        
        return {
            "content": error_message,
            "error": str(e),
            "processing_time": f"{processing_time:.3f}s"
        }

async def send_telegram_callback_answer(callback_query_id: str, text: str = "", retries=1):
    """Answer a callback query to stop the loading state on the button."""
    global TELEGRAM_BOT_TOKEN, _telegram_rate_limit
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return False
    
    # Apply rate limiting
    current_time = time.time()
    time_since_last_request = current_time - _telegram_rate_limit["last_request_time"]
    if time_since_last_request < _telegram_rate_limit["min_interval"]:
        # Sleep to respect rate limit
        await asyncio.sleep(_telegram_rate_limit["min_interval"] - time_since_last_request)
    
    # Update last request time
    _telegram_rate_limit["last_request_time"] = time.time()
    
    try:
        # Prepare the payload
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        
        # Send answerCallbackQuery via Telegram Bot API with timeout
        async with httpx.AsyncClient(timeout=3.0) as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Telegram API error answering callback: {error_text}")
                
                # If rate limited, retry after waiting
                if "Too Many Requests" in error_text and retries > 0:
                    # Extract wait time from error message, default to 1 second
                    wait_time = 1.0
                    try:
                        retry_data = response.json()
                        if retry_data.get("parameters", {}).get("retry_after"):
                            wait_time = float(retry_data["parameters"]["retry_after"])
                    except:
                        pass
                    
                    logger.warning(f"Rate limited by Telegram API, waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    
                    # Update the rate limit interval
                    _telegram_rate_limit["min_interval"] *= 1.5
                    
                    # Retry
                    return await send_telegram_callback_answer(
                        callback_query_id=callback_query_id,
                        text=text,
                        retries=retries-1
                    )
                
                return False
            
            return True
            
    except httpx.TimeoutException:
        logger.error(f"Timeout answering callback query: {callback_query_id}")
        return False
    except Exception as e:
        logger.exception(f"Error answering Telegram callback: {e}")
        return False