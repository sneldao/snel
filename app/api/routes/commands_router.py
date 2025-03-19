from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional, List
import logging
import re
import httpx
from datetime import datetime
import json

from app.models.api import CommandResponse, Command
from app.services.redis_service import RedisService
from app.services.token_service import TokenService
from app.services.pipeline import Pipeline
from app.agents.agent_factory import AgentFactory, get_agent_factory
from app.api.dependencies import get_redis_service, get_token_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["commands"])

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
        # Get user name or default to "User"
        user_name = command.user_name or "User"
        logger.info(f"Processing command from {user_name}: {command.content}")
        
        # Check if this is a Brian API command (transfer, bridge, or balance)
        content = command.content.lower()
        
        # Check for transfer, bridge, or balance commands
        if (re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", content, re.IGNORECASE) or
            (re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE) or
             re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE)) or
            re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", content, re.IGNORECASE)):
            
            # Create a Brian agent
            brian_agent = agent_factory.create_agent("brian")
            
            # Process the command with the Brian agent
            result = await brian_agent.process_brian_command(
                command=command.content,
                chain_id=command.chain_id,
                wallet_address=command.wallet_address,
                user_name=user_name  # Pass the user's name
            )
            
            # Check for errors
            if result.get("error"):
                return CommandResponse(
                    content=f"Error: {result['error']}",
                    error_message=result["error"]
                )
            
            # If this is a transaction, format it for the frontend
            if isinstance(result.get("content"), dict) and result["content"].get("type") == "transaction":
                # Store the pending command
                await redis_service.store_pending_command(
                    wallet_address=command.wallet_address or command.creator_id,
                    command=command.content
                )
                
                # Store the agent type
                await redis_service.set(
                    f"pending_command_type:{command.wallet_address or command.creator_id}",
                    "brian",
                    expire=1800  # 30 minutes
                )
                
                # Include the transaction data directly in the response
                transaction_data = result["content"].get("transaction")
                
                # If there's a transaction field at the top level, use that too
                if "transaction" in result:
                    transaction_data = result["transaction"]
                
                return CommandResponse(
                    content=result["content"],
                    metadata=result.get("metadata", {}),
                    agent_type="brian",
                    transaction=transaction_data
                )
            
            # Otherwise, return the result as is
            return CommandResponse(
                content=result.get("content", "Command processed"),
                metadata=result.get("metadata", {}),
                agent_type="brian"
            )
        
        # If not a Brian API command, process with the regular agent
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
                
                # Get the agent type for the pending command
                agent_type = await redis_service.get(f"pending_command_type:{user_id}")
                logger.info(f"Agent type for pending command: {agent_type}")
                
                # Use the pending command
                command.content = pending_command
                
                # If we have a specific agent type, route directly to that agent
                if agent_type == "swap":
                    logger.info("Routing confirmation to swap agent")
                    # Process with swap agent directly
                    swap_agent = agent_factory.create_agent("swap")
                    result = await swap_agent.process_swap_command(command.content, command.chain_id)
                    result["agent_type"] = "swap"
                    
                    # Clear the pending command and agent type
                    await redis_service.clear_pending_command(user_id)
                    await redis_service.delete(f"pending_command_type:{user_id}")
                    
                    # Return early with the swap result
                    return CommandResponse(
                        content=result.get("content", {}),
                        error_message=result.get("error"),
                        metadata=result.get("metadata", {}),
                        agent_type="swap",
                        requires_selection=result.get("requires_selection", False),
                        all_quotes=result.get("all_quotes")
                    )
                elif agent_type == "dca":
                    logger.info("Routing confirmation to DCA agent")
                    # Process with DCA agent directly
                    dca_agent = agent_factory.create_agent("dca")
                    result = await dca_agent.process_dca_command(
                        command.content, 
                        chain_id=command.chain_id,
                        wallet_address=command.wallet_address
                    )
                    result["agent_type"] = "dca"
                    
                    # Clear the pending command and agent type
                    await redis_service.clear_pending_command(user_id)
                    await redis_service.delete(f"pending_command_type:{user_id}")
                    
                    # Return early with the DCA result
                    return CommandResponse(
                        content=result.get("content", {}),
                        error_message=result.get("error"),
                        metadata=result.get("metadata", {}),
                        agent_type="dca",
                        requires_selection=result.get("requires_selection", False),
                        all_quotes=result.get("all_quotes")
                    )
                elif agent_type == "brian":
                    logger.info("Routing confirmation to Brian agent")
                    # Process with Brian agent directly
                    brian_agent = agent_factory.create_agent("brian")
                    result = await brian_agent.process_brian_command(
                        command=command.content,
                        chain_id=command.chain_id,
                        wallet_address=command.wallet_address
                    )
                    
                    # Clear the pending command and agent type
                    await redis_service.clear_pending_command(user_id)
                    await redis_service.delete(f"pending_command_type:{user_id}")
                    
                    # Get transaction data
                    transaction_data = None
                    if "transaction" in result:
                        transaction_data = result["transaction"]
                    elif isinstance(result.get("content"), dict) and "transaction" in result["content"]:
                        transaction_data = result["content"]["transaction"]
                    
                    # Return early with the Brian result
                    return CommandResponse(
                        content=result.get("content", {}),
                        error_message=result.get("error"),
                        metadata=result.get("metadata", {}),
                        agent_type="brian",
                        transaction=transaction_data
                    )
                else:
                    # If no specific agent type or unknown, use the pipeline
                    # Clear the pending command
                    await redis_service.clear_pending_command(user_id)
                    await redis_service.delete(f"pending_command_type:{user_id}")
        
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
            redis_service=redis_service
        )
        
        # Process the command using the pipeline
        result = await pipeline.process(
            command.content,
            chain_id=command.chain_id,
            wallet_address=command.wallet_address
        )
        
        # Check if we need to store a pending command
        content_type = result.get("content", {}).get("type")
        if content_type in ["swap_confirmation", "dca_confirmation"]:
            logger.info(f"Storing pending command for user {user_id}: {command.content}")
            await redis_service.set_pending_command(user_id, command.content)
            
            # Store the agent type with the pending command to ensure proper routing on confirmation
            agent_type = result.get("agent_type")
            if agent_type:
                await redis_service.set(
                    f"pending_command_type:{user_id}",
                    agent_type,
                    expire=1800  # 30 minutes
                )
            
        # Format the response
        return CommandResponse(
            content=result.get("content", {}),
            error_message=result.get("error"),
            metadata=result.get("metadata", {}),
            agent_type=result.get("agent_type", "default"),
            requires_selection=result.get("requires_selection", False),
            all_quotes=result.get("all_quotes"),
            pending_command=command.content if content_type in ["swap_confirmation", "dca_confirmation"] else None,
            awaiting_confirmation=content_type in ["swap_confirmation", "dca_confirmation"]
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
