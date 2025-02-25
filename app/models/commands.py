from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field
from eth_typing import HexAddress
from datetime import datetime
from dowse.models import Tweet, AgentMessage

class UserMessage(Tweet):
    """A message from the user."""
    id: int = 1  # Default ID for user messages
    content: str
    creator_name: str = "@user"
    creator_id: str = "anonymous"  # Changed to string type
    chain_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class BotMessage(Tweet):
    """A message from the bot."""
    id: int = 0  # Default ID for bot messages
    content: str
    creator_name: str = "@bot"
    creator_id: str = "bot"  # Changed to string type
    error_message: Optional[str] = None
    pending_command: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_agent_message(cls, msg: AgentMessage) -> 'BotMessage':
        """Create a BotMessage from an AgentMessage."""
        if not msg.content:
            return cls(
                content="Sorry, something went wrong.",
                error_message=msg.error_message,
                creator_id="bot"  # Ensure string creator_id
            )
        
        # If content is already a BotMessage, just return it
        if isinstance(msg.content, BotMessage):
            return msg.content
            
        # Otherwise create a new BotMessage
        return cls(
            content=msg.content.content if hasattr(msg.content, 'content') else str(msg.content),
            error_message=msg.error_message,
            metadata=msg.content.metadata if hasattr(msg.content, 'metadata') else None,
            creator_id="bot"  # Ensure string creator_id
        )

class CommandRequest(BaseModel):
    """API request for processing a command."""
    content: str
    creator_name: str = "@user"
    creator_id: str = "anonymous"  # Changed to string type
    chain_id: Optional[int] = None

    def to_tweet(self) -> UserMessage:
        """Convert to a Tweet for processing."""
        return UserMessage(
            content=self.content,
            creator_name=self.creator_name,
            creator_id=self.creator_id,
            chain_id=self.chain_id
        )

class CommandResponse(BaseModel):
    """API response for a processed command."""
    content: Optional[str] = None
    error_message: Optional[str] = None
    pending_command: Optional[str] = None

    @classmethod
    def from_bot_message(cls, msg: BotMessage) -> 'CommandResponse':
        """Create a CommandResponse from a BotMessage."""
        return cls(
            content=msg.content,
            error_message=msg.error_message,
            pending_command=msg.metadata.get("pending_command") if msg.metadata else None
        )

class TransactionRequest(BaseModel):
    """API request for executing a transaction."""
    command: str
    wallet_address: HexAddress
    chain_id: int
    metadata: Optional[Dict[str, Any]] = None

class TransactionResponse(BaseModel):
    """API response for a transaction execution."""
    to: HexAddress
    data: str
    value: str
    chain_id: int
    method: str
    gas_limit: str
    gas_price: Optional[str] = None
    max_fee_per_gas: Optional[str] = None
    max_priority_fee_per_gas: Optional[str] = None
    needs_approval: bool = False
    token_to_approve: Optional[HexAddress] = None
    spender: Optional[HexAddress] = None
    pending_command: Optional[str] = None

class SwapDetails(BaseModel):
    """Structured swap command details."""
    amount: float
    token_in: str
    token_out: str
    chain_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class SwapCommand(BaseModel):
    """A command to swap tokens."""
    action: Literal["swap", "price", "unknown"]
    amount: Optional[float] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    is_target_amount: bool = False  # True if amount refers to token_out
    amount_is_usd: bool = False  # True if amount is in USD
    natural_command: Optional[str] = None  # The original command text
    token_in_name: Optional[str] = None  # Full name of token_in
    token_out_name: Optional[str] = None  # Full name of token_out
    
    @property
    def amount_in(self) -> Optional[float]:
        """Alias for amount."""
        return self.amount if not self.is_target_amount else None
        
    @property
    def amount_out(self) -> Optional[float]:
        """Amount of output token."""
        return self.amount if self.is_target_amount else None 