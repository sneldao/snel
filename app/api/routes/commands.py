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
    token_service: TokenService = Depends(get_token_service)
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
            return CommandResponse(
                content="Please confirm the transaction in your wallet.",
                pending_command="confirm",
                agent_type="swap"
            )
        elif is_cancellation:
            return CommandResponse(
                content="Transaction cancelled.",
                agent_type="swap"
            )
        
        # Check if this is a swap-related query
        is_swap_related = any(word in command.content.lower() for word in ["swap", "token", "price", "approve", "allowance", "liquidity"])
        
        if is_swap_related:
            # Use the SwapAgent for swap-related queries
            provider = OpenAIProvider(
                api_key=openai_key,
                default_model=OpenAIModelType.gpt4o_mini
            )
            swap_agent = SwapAgent(provider=provider)
            
            # Process the swap command
            result = await swap_agent.process_swap(command.content, command.chain_id)
            
            if result["error"]:
                return CommandResponse(
                    error_message=result["error"],
                    agent_type="swap"
                )
            
            # Check if the content is a structured message
            if isinstance(result["content"], dict) and result["content"].get("type") == "swap_confirmation":
                # Return the structured message directly
                return CommandResponse(
                    content=result["content"],
                    pending_command=result["metadata"].get("pending_command"),
                    agent_type="swap",
                    metadata=result["metadata"]
                )
            else:
                # Return the text content
                return CommandResponse(
                    content=result["content"],
                    pending_command=result["metadata"].get("pending_command"),
                    agent_type="swap",
                    metadata=result["metadata"]
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