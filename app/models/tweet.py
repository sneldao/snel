"""
Minimal implementations of Tweet and AgentMessage classes to replace dowse dependency.
"""
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime

class Tweet(BaseModel):
    """Basic Tweet model that was previously imported from dowse."""
    id: int = 0
    content: str = ""
    creator_id: str = ""
    creator_name: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class AgentMessage(BaseModel):
    """Basic AgentMessage model that was previously imported from dowse."""
    content: Any = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict) 