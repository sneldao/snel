from typing import Optional, Any, Dict, List
from pydantic import BaseModel

class Command(BaseModel):
    """Command model for processing user commands."""
    content: str
    wallet_address: Optional[str] = None
    chain_id: int = 1
    creator_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CommandResponse(BaseModel):
    """Response model for command processing."""
    content: Optional[Any] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_type: Optional[str] = None
    requires_selection: bool = False
    all_quotes: Optional[List[Dict[str, Any]]] = None
    pending_command: Optional[str] = None
    awaiting_confirmation: bool = False
    transaction: Optional[Dict[str, Any]] = None 