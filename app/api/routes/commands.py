from fastapi import APIRouter, Depends, Request, HTTPException
import logging
from eth_utils import to_checksum_address
from app.models.commands import CommandRequest, CommandResponse, BotMessage
from app.services.command_store import CommandStore
from app.api.dependencies import get_openai_key, get_pipeline, get_command_store, get_token_service
from app.agents.swap_agent import SwapAgent
from app.agents.price_agent import PriceAgent
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.services.token_service import TokenService
from emp_agents.providers import OpenAIProvider, OpenAIModelType
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

def get_openai_key(request: Request) -> str:
    """Get OpenAI API key from request headers."""
    openai_key = request.headers.get("X-OpenAI-Key")
    if not openai_key:
        # Use environment variable as fallback
        import os
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            raise HTTPException(status_code=400, detail="OpenAI API key is required")
    return openai_key

@router.post("/process-command", response_model=CommandResponse)
async def process_command(
    command: CommandRequest,
    request: Request,
    token_service: TokenService = Depends(get_token_service),
    command_store: CommandStore = Depends(get_command_store)
):
    """Process a command and return a response."""
    try:
        # Get OpenAI API key
        openai_key = get_openai_key(request)
        
        # Check if this is a confirmation or cancellation
        is_confirmation = command.content.lower().strip() in ["yes", "confirm"]
        is_cancellation = command.content.lower().strip() in ["no", "cancel"]
        
        # If it's a confirmation or cancellation, handle it differently
        if is_confirmation:
            # Get the pending command from the store
            pending_command_data = command_store.get_command(command.creator_id)
            
            if pending_command_data:
                logger.info(f"Confirming pending command for user {command.creator_id}: {pending_command_data}")
                
                # Extract the command and chain_id
                pending_command = pending_command_data.get("command")
                chain_id = pending_command_data.get("chain_id")
                
                if pending_command and chain_id:
                    # Update the command status
                    command_store.store_command(
                        command.creator_id, 
                        pending_command, 
                        chain_id
                    )
                    
                    logger.info(f"Confirmed command: {pending_command} for chain {chain_id}")
                    
                    return CommandResponse(
                        content="Please confirm the transaction in your wallet.",
                        pending_command=pending_command,
                        agent_type="swap",
                        metadata={
                            "chain_id": chain_id,
                            "status": "confirmed"
                        }
                    )
                else:
                    logger.error(f"Invalid pending command data: {pending_command_data}")
                    return CommandResponse(
                        content="Sorry, I couldn't find a valid pending command to confirm. Please try your request again.",
                        error="No valid pending command found",
                        agent_type="swap"
                    )
            else:
                logger.error(f"No pending command found for user {command.creator_id}")
                return CommandResponse(
                    content="Sorry, I couldn't find a pending command to confirm. Please try your request again.",
                    error="No pending command found",
                    agent_type="swap"
                )
        elif is_cancellation:
            # Get the pending command from the store
            pending_command_data = command_store.get_command(command.creator_id)
            
            if pending_command_data:
                logger.info(f"Cancelling pending command for user {command.creator_id}: {pending_command_data}")
                
                # Clear the command from the store
                command_store.clear_command(command.creator_id)
                
                return CommandResponse(
                    content="Transaction cancelled. Is there anything else you'd like to do?",
                    agent_type="swap"
                )
            else:
                logger.warning(f"No pending command found to cancel for user {command.creator_id}")
                return CommandResponse(
                    content="There's no pending transaction to cancel. Is there anything else you'd like to do?",
                    agent_type="swap"
                )
        
        # Process the command based on its type
        if command.content.lower().startswith("swap"):
            # Process as a swap command
            provider = OpenAIProvider(api_key=openai_key, model=OpenAIModelType.gpt4o)
            swap_agent = SwapAgent(provider=provider)
            
            # Process the swap request
            result = await swap_agent.process_swap(command.content, command.chain_id)
            
            if result["error"]:
                return CommandResponse(
                    content=result["error"],
                    error=result["error"],
                    agent_type="swap"
                )
            
            # If we have a valid swap confirmation, store the command for later
            if result["content"] and result["content"].get("type") == "swap_confirmation":
                # Extract the pending command from the metadata
                pending_command = result["metadata"].get("pending_command")
                if pending_command:
                    # Store the command in Redis
                    logger.info(f"Storing pending swap command for user {command.creator_id}: {pending_command}")
                    command_store.store_command(
                        command.creator_id,
                        pending_command,
                        command.chain_id
                    )
            
            return CommandResponse(
                content=result["content"],
                metadata=result["metadata"],
                agent_type="swap",
                awaiting_confirmation=True if not result["error"] else False
            )
        else:
            # Use the Dowse pipeline for general queries
            pipeline = get_pipeline(openai_key)
            
            # Convert the command to a Tweet
            tweet = command.to_tweet()
            
            # Process the command
            result = await pipeline.process(tweet)
            
            # Convert the result to a BotMessage
            bot_message = BotMessage.from_agent_message(result)
            
            # Convert the BotMessage to a CommandResponse
            response = CommandResponse.from_bot_message(bot_message)
            
            return response
            
    except Exception as e:
        logger.error(f"Error processing command: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 