from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal
import logging
import json
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local", override=True)  # Override with .env.local if it exists

from app.api.dependencies import get_redis_service, get_token_service, get_wallet_service, get_wallet_service_factory, get_gemini_service
from app.agents.agent_factory import get_agent_factory
from app.services.pipeline import Pipeline
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.agents.messaging_agent import MessagingAgent
from app.services.swap_service import SwapService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.telegram_agent import TelegramAgent
from app.services.wallet_service import WalletService
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["messaging"])

# Environment variables for messaging platforms
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
logger.info(f"Loaded TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}... from environment")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

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
    wallet_service: WalletService = Depends(get_wallet_service_factory),
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> TelegramAgent:
    """Get an instance of TelegramAgent."""
    # Create a simple swap agent for the swap service
    swap_agent = SimpleSwapAgent()
    
    # Create a swap service for the telegram agent
    swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
    
    # Create and return the telegram agent
    return TelegramAgent(
        token_service=token_service,
        swap_service=swap_service,
        wallet_service=wallet_service,
        gemini_service=gemini_service
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
        logger.info(f"Received Telegram webhook: {body.get('update_id', 'unknown')}")
        
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
    """Process a Telegram webhook update in the background."""
    try:
        # Log the entire update for debugging
        logger.info(f"Processing Telegram webhook: {json.dumps(update_dict, indent=2)}")
        
        # Create dependencies
        redis_service = RedisService(redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        token_service = TokenService()
        
        # Get wallet service - Always prefer SmartWalletService when CDP_SDK is enabled
        if os.getenv("USE_CDP_SDK", "false").lower() in ["true", "1", "yes"]:
            try:
                from app.services.smart_wallet_service import SmartWalletService
                wallet_service = SmartWalletService(redis_url=os.environ.get("REDIS_URL"))
                logger.info("Using SmartWalletService for Telegram webhook")
            except Exception as e:
                logger.error(f"Error initializing SmartWalletService: {e}")
                logger.warning("Falling back to basic WalletService - CDP features will be unavailable")
                wallet_service = WalletService(redis_service=redis_service)
        else:
            logger.info("USE_CDP_SDK is disabled, using basic WalletService")
            wallet_service = WalletService(redis_service=redis_service)
        
        # Create swap agent and service
        swap_agent = SimpleSwapAgent()
        swap_service = SwapService(token_service=token_service, swap_agent=swap_agent)
        
        # Create Gemini service for AI responses
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        gemini_service = GeminiService(api_key=gemini_api_key) if gemini_api_key else None
        
        # Create the telegram agent
        telegram_agent = TelegramAgent(
            token_service=token_service,
            swap_service=swap_service,
            wallet_service=wallet_service,
            gemini_service=gemini_service
        )
        
        # Extract user_id from the update based on the update type
        user_id = None
        message_text = None
        
        if update_dict.get("message", {}) and update_dict["message"].get("from", {}).get("id"):
            user_id = update_dict["message"]["from"]["id"]
            message_text = update_dict["message"].get("text", "")
            logger.info(f"Telegram message from user {user_id}: '{message_text}'")
        elif update_dict.get("callback_query", {}) and update_dict["callback_query"].get("from", {}).get("id"):
            user_id = update_dict["callback_query"]["from"]["id"]
            callback_data = update_dict["callback_query"].get("data", "")
            logger.info(f"Telegram callback from user {user_id}: '{callback_data}'")
        
        if not user_id:
            logger.warning("No user_id found in Telegram update")
            return
        
        # Check if user has a linked wallet
        wallet_address = None
        key = f"messaging:telegram:user:{user_id}:wallet"
        wallet_address = await redis_service.get(key)
        
        # Process the update with the TelegramAgent
        result = await telegram_agent.process_telegram_update(
            update=update_dict,
            user_id=str(user_id),
            wallet_address=wallet_address
        )
        
        # If result contains a callback query answer, send it back
        callback_query_id = update_dict.get("callback_query", {}).get("id")
        if callback_query_id:
            await send_telegram_callback_answer(callback_query_id)
        
        # If there's a wallet address in the result, store it
        if result.get("wallet_address") is not None:
            if result.get("wallet_address"):  # Non-empty wallet address
                await redis_service.set(
                    key=f"messaging:telegram:user:{user_id}:wallet",
                    value=result["wallet_address"]
                )
                # Also store the reverse mapping
                await redis_service.set(
                    key=f"wallet:{result['wallet_address']}:telegram:user",
                    value=str(user_id)
                )
            else:  # Empty wallet address = disconnect wallet
                # Delete the mappings
                old_wallet = await redis_service.get(f"messaging:telegram:user:{user_id}:wallet")
                if old_wallet:
                    await redis_service.delete(f"wallet:{old_wallet}:telegram:user")
                await redis_service.delete(f"messaging:telegram:user:{user_id}:wallet")
        
        # Send response back to the user
        content = result.get("content", "")
        if content:
            # Check if there are any Telegram-specific buttons to include
            buttons = None
            if result.get("metadata", {}) and result["metadata"].get("telegram_buttons"):
                buttons = result["metadata"]["telegram_buttons"]
                
            # Send the message with optional buttons
            chat_id = None
            if update_dict.get("message", {}) and update_dict["message"].get("chat", {}).get("id"):
                chat_id = update_dict["message"]["chat"]["id"]
            elif update_dict.get("callback_query", {}) and update_dict["callback_query"].get("message", {}).get("chat", {}).get("id"):
                chat_id = update_dict["callback_query"]["message"]["chat"]["id"]
                
            if chat_id:
                await send_telegram_message_with_buttons(
                    chat_id=str(chat_id),
                    message=content,
                    buttons=buttons
                )
        
        logger.info(f"Successfully processed Telegram update for user {user_id}")
        
    except Exception as e:
        logger.exception(f"Error processing Telegram webhook in background: {e}")

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
        token_preview = TELEGRAM_BOT_TOKEN[:5] + "..." if TELEGRAM_BOT_TOKEN else "None"
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
    telegram_agent: TelegramAgent = Depends(get_telegram_agent),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Process a Telegram message from the dedicated Telegram bot.
    
    This endpoint is separate from the webhook to isolate the bot functionality
    from the web interface.
    """
    try:
        # Check if this is coming from our Telegram bot
        metadata = request.metadata or {}
        is_from_bot = metadata.get("source") == "telegram_bot"
        
        logger.info(f"Processing Telegram request from {'bot' if is_from_bot else 'webhook'} for user {request.user_id}")
        
        # Add more verbose logging for debugging
        if is_from_bot:
            logger.info(f"Bot version: {metadata.get('version')}, timestamp: {metadata.get('timestamp')}")
        
        # Check if user has a linked wallet
        wallet_address = None
        if redis_service:
            key = f"messaging:telegram:user:{request.user_id}:wallet"
            wallet_address = await redis_service.get(key)
        
        # Process the message using the Telegram agent
        result = await telegram_agent._process_telegram_message(
            message=request.message,
            user_id=request.user_id,
            wallet_address=wallet_address,
            metadata=request.metadata
        )
        
        # If there's a wallet address in the result, store it
        if result.get("wallet_address") is not None:
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
        
        # Add a flag for the bot to identify this response
        if is_from_bot:
            if not result.get("metadata"):
                result["metadata"] = {}
            result["metadata"]["telegram_bot_response"] = True
        
        return result
        
    except Exception as e:
        logger.exception(f"Error processing Telegram request: {e}")
        return {
            "content": f"Sorry, I encountered an error: {str(e)}",
            "error": str(e)
        }

async def send_telegram_message_with_buttons(chat_id: str, message: str, buttons=None):
    """Send a message via Telegram Bot API with optional inline buttons."""
    global TELEGRAM_BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured, attempting to reload from environment")
        reload_environment_variables()
        if not TELEGRAM_BOT_TOKEN:
            logger.error("Failed to load Telegram bot token from environment")
            return
    
    try:
        # Log the token (first few characters) for debugging
        token_preview = TELEGRAM_BOT_TOKEN[:5] + "..." if TELEGRAM_BOT_TOKEN else "None"
        logger.info(f"Sending Telegram message to {chat_id} using token: {token_preview}")
        
        # Prepare request payload
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"  # Allow HTML formatting
        }
        
        # Add reply markup if buttons are provided
        if buttons:
            payload["reply_markup"] = {
                "inline_keyboard": buttons
            }
        
        # Send message via Telegram Bot API
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            logger.info(f"Sending request to: {url}")
            
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

async def send_telegram_callback_answer(callback_query_id: str, text: str = ""):
    """Answer a callback query to stop the loading state on the button."""
    global TELEGRAM_BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return
    
    try:
        # Send answerCallbackQuery via Telegram Bot API
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            
            payload = {
                "callback_query_id": callback_query_id,
            }
            
            if text:
                payload["text"] = text
            
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Telegram API error answering callback: {response.text}")
            
    except Exception as e:
        logger.exception(f"Error answering Telegram callback: {e}")

@router.get("/telegram/debug")
async def debug_telegram_agent(
    telegram_agent: TelegramAgent = Depends(get_telegram_agent)
):
    """Debug endpoint to check TelegramAgent initialization."""
    try:
        # Check if the wallet_service is properly initialized
        wallet_service_type = type(telegram_agent.wallet_service).__name__ if telegram_agent.wallet_service else "None"
        wallet_service_initialized = telegram_agent.wallet_service is not None
        
        # Check if the command handlers are set up
        command_handlers = list(telegram_agent.command_handlers.keys()) if telegram_agent.command_handlers else []
        
        # Return debug info
        return {
            "status": "ok",
            "agent_type": type(telegram_agent).__name__,
            "wallet_service_type": wallet_service_type,
            "wallet_service_initialized": wallet_service_initialized,
            "command_handlers": command_handlers,
            "model_config": getattr(telegram_agent, "model_config", {}),
        }
    except Exception as e:
        logger.exception(f"Error in debug endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "traceback": f"{e.__class__.__name__}: {str(e)}"
        }

@router.get("/check-cdp-config")
async def check_cdp_config():
    """Check the Coinbase Developer Platform configuration."""
    # Check environment variables
    cdp_api_key_name = os.environ.get("CDP_API_KEY_NAME")
    cdp_api_key_private_key = os.environ.get("CDP_API_KEY_PRIVATE_KEY")
    use_cdp_sdk = os.environ.get("USE_CDP_SDK", "false").lower() in ["true", "1", "yes"]
    cdp_use_managed_wallet = os.environ.get("CDP_USE_MANAGED_WALLET", "false").lower() in ["true", "1", "yes"]
    
    # Check for CDP SDK module
    try:
        import cdp
        cdp_sdk_installed = True
        cdp_sdk_version = getattr(cdp, "__version__", "unknown")
    except ImportError:
        cdp_sdk_installed = False
        cdp_sdk_version = None
        
    # Check for the SmartWalletService
    try:
        from app.services.smart_wallet_service import SmartWalletService
        smart_wallet_available = True
    except ImportError:
        smart_wallet_available = False
        
    # Try initializing the SmartWalletService if all prerequisites are met
    smart_wallet_service = None
    initialization_error = None
    if (use_cdp_sdk and cdp_sdk_installed and smart_wallet_available and
        cdp_api_key_name and cdp_api_key_private_key):
        try:
            from app.services.smart_wallet_service import SmartWalletService
            smart_wallet_service = SmartWalletService(redis_url=os.environ.get("REDIS_URL"))
            smart_wallet_initialized = True
        except Exception as e:
            smart_wallet_initialized = False
            initialization_error = str(e)
    else:
        smart_wallet_initialized = False
        
    # Prepare recommendations
    recommendations = []
    
    if not cdp_sdk_installed:
        recommendations.append("Install CDP SDK: pip install cdp-sdk")
        
    if not cdp_api_key_name:
        recommendations.append("Set CDP_API_KEY_NAME environment variable")
        
    if not cdp_api_key_private_key:
        recommendations.append("Set CDP_API_KEY_PRIVATE_KEY environment variable")
        
    if not use_cdp_sdk:
        recommendations.append("Set USE_CDP_SDK=true in environment variables")
        
    if not smart_wallet_available:
        recommendations.append("Ensure app/services/smart_wallet_service.py exists and is importable")
        
    if initialization_error:
        recommendations.append(f"Fix SmartWalletService initialization error: {initialization_error}")
        
    # Return the results
    return {
        "cdp_sdk_installed": cdp_sdk_installed,
        "cdp_sdk_version": cdp_sdk_version,
        "smart_wallet_available": smart_wallet_available,
        "environment_variables": {
            "CDP_API_KEY_NAME": bool(cdp_api_key_name),
            "CDP_API_KEY_PRIVATE_KEY": bool(cdp_api_key_private_key),
            "USE_CDP_SDK": use_cdp_sdk,
            "CDP_USE_MANAGED_WALLET": cdp_use_managed_wallet
        },
        "smart_wallet_initialized": smart_wallet_initialized,
        "initialization_error": initialization_error,
        "recommendations": recommendations,
        "status": "ready" if smart_wallet_initialized else "not_ready"
    }
