"""
Chat command processing endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatCommand(BaseModel):
    """Chat command request model."""
    command: str
    wallet_address: Optional[str] = None
    chain_id: Optional[int] = None

class ChatResponse(BaseModel):
    """Chat command response model."""
    message: str
    error: Optional[str] = None

@router.post("/process-command", response_model=ChatResponse)
async def process_command(command: ChatCommand):
    """Process a chat command."""
    try:
        # For now, just echo back the command
        return ChatResponse(
            message=f"Received command: {command.command}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
