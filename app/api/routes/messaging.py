"""
API routes for messaging platforms integration.
"""
import logging
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
# Import at function level instead
# from app.agents.telegram_agent import TelegramAgent
from app.api.dependencies import get_telegram_agent
from app.services.wallet_service import WalletService
from app.api.dependencies import get_wallet_service
from app.api.routes.messaging_router import process_telegram_webhook

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process")
async def process_telegram_message(
    request: Request,
    background_tasks: BackgroundTasks,
    telegram_agent: Any = Depends(get_telegram_agent),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> Dict[str, Any]:
    """
    Process incoming Telegram messages and generate responses.
    
    Args:
        request: FastAPI request object
        background_tasks: FastAPI background tasks
        telegram_agent: TelegramAgent for handling Telegram-specific logic
        wallet_service: WalletService for wallet operations
        
    Returns:
        Response with content for Telegram
    """
    try:
        # Parse the request data
        data = await request.json()
        logger.info(f"Received Telegram message: {json.dumps(data)[:500]}...")
        
        # Extract the relevant information
        message_data = None
        callback_query = None
        
        # Check for text message
        if "message" in data and "text" in data["message"]:
            message_data = {
                "text": data["message"]["text"],
                "user_id": str(data["message"]["from"]["id"]),
                "username": data["message"]["from"].get("username", "")
            }
        # Check for callback query (inline button press)
        elif "callback_query" in data:
            callback_query = {
                "data": data["callback_query"]["data"],
                "user_id": str(data["callback_query"]["from"]["id"]),
                "username": data["callback_query"]["from"].get("username", "")
            }
        else:
            logger.warning("Unsupported message type")
            return {"content": "I don't understand this message type yet."}
        
        # Process different message types
        if message_data:
            # Get user's wallet address if it exists
            wallet_address = None
            try:
                wallet_info = await wallet_service.get_wallet_info(message_data["user_id"], "telegram")
                if wallet_info and "wallet_address" in wallet_info:
                    wallet_address = wallet_info["wallet_address"]
            except Exception as e:
                logger.exception(f"Error retrieving wallet for user {message_data['user_id']}: {e}")
            
            # Extract command and arguments if present
            message_text = message_data["text"]
            is_command = message_text.startswith('/')
            
            if is_command:
                # Split into command and arguments
                parts = message_text.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                logger.info(f"Processing command: {command} with args: {args}")
                
                # Process command through the telegram agent
                response = await telegram_agent.process_command(
                    command=command,
                    args=args,
                    user_id=message_data["user_id"],
                    wallet_address=wallet_address
                )
            else:
                # Process regular message
                logger.info(f"Processing regular message: {message_text[:50]}...")
                
                response = await telegram_agent.process_message(
                    message=message_text,
                    platform="telegram",
                    user_id=message_data["user_id"],
                    wallet_address=wallet_address
                )
            
            # Check if wallet_address has changed
            if response.get("wallet_address") is not None and response["wallet_address"] != wallet_address:
                # Handle wallet setup or changes
                logger.info(f"Updating wallet for user {message_data['user_id']}")
                if response["wallet_address"] is None:
                    # Wallet was disconnected
                    background_tasks.add_task(
                        wallet_service.delete_wallet,
                        user_id=message_data["user_id"],
                        platform="telegram"
                    )
            
            return response
            
        elif callback_query:
            # Get user's wallet address if it exists
            wallet_address = None
            try:
                wallet_info = await wallet_service.get_wallet_info(callback_query["user_id"], "telegram")
                if wallet_info and "wallet_address" in wallet_info:
                    wallet_address = wallet_info["wallet_address"]
            except Exception as e:
                logger.exception(f"Error retrieving wallet for user {callback_query['user_id']}: {e}")
            
            # Process callback query
            logger.info(f"Processing callback: {callback_query['data']}")
            
            response = await telegram_agent.process_callback_query(
                user_id=callback_query["user_id"],
                callback_data=callback_query["data"],
                wallet_address=wallet_address
            )
            
            # Check if wallet_address has changed
            if response.get("wallet_address") is not None and response["wallet_address"] != wallet_address:
                # Handle wallet setup or changes
                logger.info(f"Updating wallet for user {callback_query['user_id']}")
                if response["wallet_address"] is None:
                    # Wallet was disconnected
                    background_tasks.add_task(
                        wallet_service.delete_wallet,
                        user_id=callback_query["user_id"],
                        platform="telegram"
                    )
                else:
                    # New wallet was connected - this should be handled in the callback handler already
                    pass
            
            return response
        
        return {"content": "Unsupported message type"}
        
    except Exception as e:
        logger.exception(f"Error processing Telegram message: {e}")
        return {"content": "Sorry, I encountered an error processing your message."}

@router.post("/webhook")
async def telegram_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Handle Telegram webhook requests.
    
    This endpoint is specifically for receiving webhook events from Telegram.
    """
    try:
        # Get the raw request body
        body = await request.json()
        logger.info(f"Received webhook request from Telegram with update_id: {body.get('update_id', 'unknown')}")
        
        # Process in background to avoid timeouts
        background_tasks.add_task(process_telegram_webhook, body)
        
        # Return success immediately to avoid timeouts
        return {"status": "processing"}
    except Exception as e:
        logger.exception(f"Error in webhook handler: {e}")
        return {"status": "error", "message": str(e)} 