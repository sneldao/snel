from fastapi import APIRouter, Depends, Request, HTTPException
import logging
from eth_utils import to_checksum_address
from app.models.commands import CommandRequest, CommandResponse, BotMessage
from app.services.command_store import CommandStore
from app.api.dependencies import get_openai_key, get_pipeline, get_command_store
from app.agents.swap_agent import SwapAgent
from app.agents.price_agent import PriceAgent

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/process-command")
async def process_command(
    request: Request,
    command_request: CommandRequest,
    command_store: CommandStore = Depends(get_command_store),
    openai_key: str = Depends(get_openai_key)
):
    try:
        # Get pipeline instance
        pipeline = get_pipeline(openai_key)
        
        # Normalize user ID - ALWAYS use lowercase for consistency
        original_id = command_request.creator_id
        user_id = command_request.creator_id.lower()
        
        # Log the normalization for debugging
        logger.info(f"User ID normalization: Original: {original_id}, Normalized: {user_id}")
        
        # Update the request with normalized ID
        command_request.creator_id = user_id
        
        logger.info(f"Processing command: {command_request.content} on chain {command_request.chain_id}")
        logger.info(f"User ID (normalized): {user_id}, Name: {command_request.creator_name}")
        
        # Handle confirmations
        content = command_request.content.lower().strip()
        if content in ["yes", "y", "confirm"]:
            # Get pending command
            pending_command = command_store.get_command(user_id)
            if pending_command:
                logger.info(f"Found pending command for user {user_id}: {pending_command}")
                return CommandResponse(
                    content=f"Great! I'll execute your swap. Please approve the transaction in your wallet.",
                    pending_command=pending_command["command"]
                )
            else:
                # Debug: List all pending commands to help diagnose the issue
                all_commands = command_store.list_all_commands()
                logger.warning(f"No pending command found for user {user_id}. All pending commands: {all_commands}")
                
                # Try to find a command with a similar user ID (case-insensitive)
                similar_command = None
                for cmd in all_commands:
                    if cmd.get("user_id", "").lower() == user_id.lower():
                        similar_command = cmd
                        logger.info(f"Found command with similar user ID: {similar_command}")
                        break
                
                if similar_command:
                    # Use the command with the similar user ID
                    logger.info(f"Using command with similar user ID: {similar_command}")
                    return CommandResponse(
                        content=f"Great! I'll execute your swap. Please approve the transaction in your wallet.",
                        pending_command=similar_command["command"]
                    )
                
                return CommandResponse(
                    content="I don't have any pending commands to confirm. Please submit a new swap request.",
                    error_message="No pending command found"
                )
        
        # Handle cancellations
        if content in ["no", "n", "cancel"]:
            # Clear pending command
            command_store.clear_command(user_id)
            return CommandResponse(
                content="I've cancelled your request. How else can I help you?"
            )
            
        # Convert request to Tweet
        tweet = command_request.to_tweet()
        
        # Process through pipeline
        result = await pipeline.process(tweet)
        logger.info(f"Pipeline result: {result}")
        
        # Handle pipeline errors
        if result.error_message:
            return CommandResponse(
                content=f"Sorry, I couldn't process your command: {result.error_message}",
                error_message=result.error_message
            )
        
        # Convert result to BotMessage
        bot_message = BotMessage.from_agent_message(result)
        
        # Store pending command if one was generated
        if bot_message.metadata and "pending_command" in bot_message.metadata:
            logger.info(f"Storing pending command for user {user_id}: {bot_message.metadata['pending_command']}")
            command_store.store_command(
                user_id,
                bot_message.metadata["pending_command"],
                command_request.chain_id
            )
            
            # Verify storage immediately
            stored = command_store.get_command(user_id)
            if not stored:
                logger.error(f"Failed to verify command storage for user {user_id}")
                raise RuntimeError("Failed to store command")
        
        # Convert BotMessage to API response
        response = CommandResponse.from_bot_message(bot_message)
        
        # Add pending command to response if it exists
        if bot_message.metadata and "pending_command" in bot_message.metadata:
            response.pending_command = bot_message.metadata["pending_command"]
            
        return response
            
    except Exception as e:
        logger.error(f"Unexpected error in command processing: {e}", exc_info=True)
        return CommandResponse(
            content="Sorry, something went wrong. Please try again!",
            error_message=str(e)
        ) 