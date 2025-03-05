from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal
from app.api.dependencies import get_redis_service, get_token_service
from app.agents.agent_factory import AgentFactory, get_agent_factory
from app.services.pipeline import Pipeline
from app.services.token_service import TokenService
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)
router = APIRouter(tags=["commands"])

class Command(BaseModel):
    """
    Represents a command sent by a user.
    """
    content: str
    creator_name: str = "User"
    creator_id: str = "anonymous"
    chain_id: int = 1
    wallet_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CommandResponse(BaseModel):
    """
    Represents a response to a command.
    """
    content: Dict[str, Any]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_type: Optional[str] = None
    requires_selection: bool = False
    all_quotes: Optional[List[Dict[str, Any]]] = None
    pending_command: Optional[str] = None
    awaiting_confirmation: bool = False

@router.post("/process-command", response_model=CommandResponse)
async def process_command(
    command: Command,
    request: Request,
    redis_service = Depends(get_redis_service),
    agent_factory: AgentFactory = Depends(get_agent_factory),
    token_service = Depends(get_token_service)
):
    """
    Process a command from the user.
    """
    try:
        logger.info(f"Processing command: {command.content}")
        
        # Store the user ID or wallet address for consistent identification
        user_id = command.wallet_address or command.creator_id
        
        # Check if this is a confirmation of a previous command
        content = command.content.strip().lower()
        
        if content in ["yes", "confirm", "approved", "ok", "go ahead"]:
            logger.info(f"Confirmation received for user {user_id}")
            
            # Check for a pending command in Redis
            pending_command = await redis_service.get_pending_command(user_id)
            if pending_command:
                logger.info(f"Found pending command for user {user_id}: {pending_command}")
                
                # Use the pending command
                command.content = pending_command
                
                # Clear the pending command
                await redis_service.clear_pending_command(user_id)
        
        # Store the command for reference
        timestamp = datetime.now().isoformat()
        await redis_service.set(
            f"command_history:{user_id}:{timestamp}",
            {
                "command": command.content,
                "timestamp": timestamp,
                "metadata": command.metadata or {}
            },
            expire=86400  # Store for 24 hours
        )
        
        # Create a pipeline to process the command
        pipeline = Pipeline(
            token_service=token_service,
            swap_agent=agent_factory.create_agent("swap"),
            price_agent=agent_factory.create_agent("price"),
            dca_agent=agent_factory.create_agent("dca"),
            redis_service=redis_service
        )
        
        # Process the command using the pipeline
        result = await pipeline.process(
            command.content,
            chain_id=command.chain_id,
            wallet_address=command.wallet_address
        )
        
        # Check if we need to store a pending command
        if result.get("type") in ["swap_confirmation", "dca_confirmation"]:
            logger.info(f"Storing pending command for user {user_id}: {command.content}")
            await redis_service.set_pending_command(user_id, command.content)
            
        # Format the response
        return CommandResponse(
            content=result.get("content", {}),
            error_message=result.get("error"),
            metadata=result.get("metadata", {}),
            agent_type=result.get("agent_type", "default"),
            requires_selection=result.get("requires_selection", False),
            all_quotes=result.get("all_quotes"),
            pending_command=command.content if result.get("type") in ["swap_confirmation", "dca_confirmation"] else None,
            awaiting_confirmation=result.get("type") in ["swap_confirmation", "dca_confirmation"]
        )
            
    except Exception as e:
        logger.exception(f"Error processing command: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process command: {str(e)}"
        )

@router.post("/store-command")
async def store_command(
    user_id: str,
    command: str,
    response: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    redis_service = Depends(get_redis_service)
) -> Dict[str, bool]:
    """Store a command and its response for a user."""
    try:
        timestamp = datetime.now().isoformat()
        data = {
            "command": command,
            "response": response,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }
        
        key = f"command_history:{user_id}:{timestamp}"
        success = await redis_service.set(key, data, expire=86400)  # 24 hours
        
        return {"success": success}
    except Exception as e:
        logger.exception(f"Error storing command: {e}")
        return {"success": False}

@router.get("/command-history/{user_id}")
async def get_command_history(
    user_id: str,
    redis_service = Depends(get_redis_service)
) -> Dict[str, Any]:
    """Get command history for a user."""
    try:
        pattern = f"command_history:{user_id}:*"
        keys = await redis_service.keys(pattern)
        
        if not keys:
            return {"commands": []}
        
        # Sort keys by timestamp (assuming timestamp is part of the key)
        keys.sort()
        
        # Get all commands
        commands = []
        for key in keys:
            data = await redis_service.get(key)
            if data:
                commands.append(data)
        
        return {"commands": commands}
    except Exception as e:
        logger.exception(f"Error getting commands: {e}")
        return {"commands": [], "error": str(e)}

@router.delete("/clear-commands/{user_id}")
async def clear_commands(
    user_id: str,
    redis_service = Depends(get_redis_service)
) -> Dict[str, bool]:
    """Clear all commands for a user."""
    try:
        pattern = f"command_history:{user_id}:*"
        keys = await redis_service.keys(pattern)
        
        if not keys:
            return {"success": True}
        
        # Delete all keys
        for key in keys:
            await redis_service.delete(key)
        
        # Also clear any pending commands
        await redis_service.clear_pending_command(user_id)
        
        return {"success": True}
    except Exception as e:
        logger.exception(f"Error clearing commands: {e}")
        return {"success": False} 