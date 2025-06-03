"""
Legacy swap endpoints - forwards to unified command processor.
Maintained for backward compatibility with existing frontend code.
This eliminates 800+ lines of duplicate command processing logic.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any

from app.services.command_processor import CommandProcessor
from app.models.unified_models import ChatCommand
from app.core.dependencies import get_command_processor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/swap", tags=["swap"])

# Legacy request model for backward compatibility
class SwapCommand(BaseModel):
    command: str = Field(description="Swap command string")
    wallet_address: str = Field(description="User wallet address")
    chain_id: int = Field(description="Current chain ID")

@router.post("/process-command")
async def process_swap_command(
    cmd: SwapCommand,
    command_processor: CommandProcessor = Depends(get_command_processor)
) -> Dict[str, Any]:
    """
    Legacy swap endpoint - forwards to unified command processor.
    
    This endpoint maintains backward compatibility while eliminating
    the 800+ lines of duplicate command processing logic that was
    previously in this file.
    
    All swap processing now goes through the unified command processor
    for consistent, DRY, modular architecture.
    """
    try:
        logger.info(f"Legacy swap endpoint processing: {cmd.command}")
        
        # Convert legacy SwapCommand to unified ChatCommand
        chat_command = ChatCommand(
            command=cmd.command,
            wallet_address=cmd.wallet_address,
            chain_id=cmd.chain_id
        )
        
        # Create unified command
        unified_command = CommandProcessor.create_unified_command(
            command=chat_command.command,
            wallet_address=chat_command.wallet_address,
            chain_id=chat_command.chain_id
        )
        
        # Process through unified processor
        unified_response = await command_processor.process_command(unified_command)
        
        # Convert unified response back to legacy format for backward compatibility
        content = unified_response.content
        if hasattr(content, 'model_dump'):
            content = content.model_dump()
        elif hasattr(content, '__dict__'):
            content = content.__dict__
            
        # Return in legacy format expected by frontend
        return {
            "success": unified_response.status == "success",
            "content": content,
            "metadata": unified_response.metadata,
            "agent_type": str(unified_response.agent_type),
            "status": unified_response.status,
            "error": unified_response.error,
            "awaiting_confirmation": unified_response.awaiting_confirmation
        }
        
    except Exception as e:
        logger.exception(f"Error in legacy swap endpoint: {e}")
        return {
            "success": False,
            "message": f"Swap processing failed: {str(e)}",
            "error_details": {
                "error": str(e),
                "suggestion": "Please try again or use the main chat interface.",
                "protocols_tried": []
            }
        }

@router.get("/health")
async def swap_health() -> Dict[str, Any]:
    """Health check for swap service - now unified."""
    return {
        "status": "healthy",
        "service": "swap",
        "architecture": "unified_command_processor",
        "message": "Swap processing now handled by unified command processor",
        "eliminated_duplication": "800+ lines of duplicate logic removed"
    }

@router.get("/info")
async def swap_info() -> Dict[str, Any]:
    """Information about the swap service architecture."""
    return {
        "service": "swap",
        "architecture": "unified",
        "description": "Legacy swap endpoints that forward to unified command processor",
        "benefits": [
            "Eliminated 800+ lines of duplicate code",
            "Consistent error handling across all commands",
            "Single source of truth for command processing",
            "Easier testing and maintenance"
        ],
        "endpoints": {
            "/process-command": "Main swap processing (forwards to unified processor)",
            "/health": "Service health check",
            "/info": "Service information"
        },
        "migration_status": "Complete - all swap logic unified"
    }
