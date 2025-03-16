from typing import Optional, Literal, Dict, Any, List, Union, TypeVar
from pydantic import BaseModel, Field, root_validator, validator
from eth_typing import HexAddress
from datetime import datetime
from dowse.models import Tweet, AgentMessage
from decimal import Decimal

# Re-export Command from api.py for backward compatibility
from app.models.api import Command

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
    def from_agent_message(cls, msg: Union[AgentMessage, Dict[str, Any]]) -> 'BotMessage':
        """Create a BotMessage from an AgentMessage or dict."""
        # If we got a dict instead of an AgentMessage, convert it
        if isinstance(msg, dict):
            # Extract content, error, and metadata from the dict
            content = msg.get("content")
            error = msg.get("error")
            metadata = msg.get("metadata", {})
            
            # Create a BotMessage
            return cls(
                content=str(content) if content is not None else "Sorry, I couldn't process that request.",
                error_message=error,
                metadata=metadata,
                creator_id="bot"
            )
        
        # Now we know it's an AgentMessage
        if not msg.content:
            return cls(
                content="Sorry, something went wrong.",
                error_message=msg.error_message,
                creator_id="bot"
            )
        
        # If content is already a BotMessage, just return it
        if isinstance(msg.content, BotMessage):
            return msg.content
        
        # Handle the case when msg.content is a dict
        if isinstance(msg.content, dict):
            # Check if it has a content field, otherwise use the whole dict as content
            if "content" in msg.content:
                content = msg.content["content"]
                metadata = msg.content.get("metadata", {})
            else:
                content = str(msg.content)
                metadata = {}
            
            return cls(
                content=content,
                error_message=msg.error_message,
                metadata=metadata,
                creator_id="bot"
            )
            
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
    content: Optional[Any] = None  # Updated to accept any type
    error_message: Optional[str] = None
    pending_command: Optional[str] = None
    agent_type: Optional[str] = "default"  # Can be "default" or "swap"
    metadata: Optional[Dict[str, Any]] = None  # Added metadata field
    awaiting_confirmation: bool = False

    @classmethod
    def from_bot_message(cls, msg: BotMessage) -> 'CommandResponse':
        """Create a CommandResponse from a BotMessage."""
        # Determine agent type based on content and metadata
        agent_type = "default"
        
        # Safely handle content which could be of various types
        if isinstance(msg.content, str):
            content = msg.content
        elif msg.content is None:
            content = ""
        else:
            try:
                content = str(msg.content)
            except Exception:
                content = "Message content cannot be displayed"
        
        metadata = msg.metadata or {}
        
        # Check if this is a swap-related message
        if isinstance(content, str) and any(word in content.lower() for word in ["swap", "token", "approve", "allowance", "liquidity"]) or \
           metadata.get("method") == "swap" or \
           metadata.get("pending_command", "").startswith("swap"):
            agent_type = "swap"
        
        return cls(
            content=msg.content,
            error_message=msg.error_message,
            pending_command=metadata.get("pending_command"),
            agent_type=agent_type,
            metadata=metadata,
            awaiting_confirmation=metadata.get("awaiting_confirmation", False)
        )

class TransactionRequest(BaseModel):
    """API request for executing a transaction."""
    command: str
    wallet_address: HexAddress
    chain_id: int
    metadata: Optional[Dict[str, Any]] = None
    skip_approval: Optional[bool] = False
    selected_aggregator: Optional[str] = None  # Field for selected aggregator
    get_quotes: Optional[bool] = False  # New field to indicate if we should get quotes

class TransactionResponse(BaseModel):
    """API response for a transaction execution."""
    # Transaction data fields - only required for successful responses
    to: Optional[HexAddress] = None
    data: Optional[str] = None
    value: Optional[str] = None
    chain_id: Optional[int] = None
    method: Optional[str] = None
    gas_limit: Optional[str] = None
    gas_price: Optional[str] = None
    max_fee_per_gas: Optional[str] = None
    max_priority_fee_per_gas: Optional[str] = None
    
    # Error fields
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Other fields
    needs_approval: bool = False
    token_to_approve: Optional[HexAddress] = None
    spender: Optional[HexAddress] = None
    pending_command: Optional[str] = None
    agent_type: Optional[str] = "default"  # Can be "default" or "swap"
    metadata: Optional[Dict[str, Any]] = None
    
    # Aggregator selection fields
    requires_selection: bool = False
    all_quotes: Optional[List[Dict[str, Any]]] = None
    quotes_count: Optional[int] = None
    
    # Confirmation fields
    awaiting_confirmation: bool = False
    
    # Status field to clearly indicate the response type
    status: Literal["success", "error", "needs_clarification", "requires_selection", "awaiting_confirmation"] = "success"
    
    # Field for missing information that needs clarification
    missing_info: Optional[List[str]] = None
    clarification_prompt: Optional[str] = None
    
    def __init__(self, **data):
        # If this is an error response, set the status to error
        if 'error' in data and data['error']:
            data['status'] = 'error'
            
        # If this needs clarification, set the status accordingly
        if 'missing_info' in data and data['missing_info']:
            data['status'] = 'needs_clarification'
            
        # If this requires selection, set the status accordingly
        if 'requires_selection' in data and data['requires_selection']:
            data['status'] = 'requires_selection'
            
        # If this is awaiting confirmation, set the status accordingly
        if 'awaiting_confirmation' in data and data['awaiting_confirmation']:
            data['status'] = 'awaiting_confirmation'
            
        super().__init__(**data)

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
    amount_in: Optional[float] = None  # Changed from amount to amount_in
    token_in: Optional[Union[str, Dict[str, Any]]] = None  # Allow dictionary for token info
    token_out: Optional[Union[str, Dict[str, Any]]] = None  # Allow dictionary for token info
    is_target_amount: bool = False  # True if amount refers to token_out
    amount_is_usd: bool = False  # True if amount is in USD
    natural_command: Optional[str] = None  # The original command text
    token_in_name: Optional[str] = None  # Full name of token_in
    token_out_name: Optional[str] = None  # Full name of token_out
    slippage: float = 0.5  # Default slippage percentage
    
    # Add a custom init method to handle 'amount' parameter
    def __init__(self, **data):
        # If 'amount' is provided, use it for amount_in
        if 'amount' in data and 'amount_in' not in data:
            data['amount_in'] = data.pop('amount')
        super().__init__(**data)
    
    @property
    def amount(self) -> Optional[float]:
        """Alias for amount_in for backward compatibility."""
        return self.amount_in
        
    @property
    def amount_out(self) -> Optional[float]:
        """Amount of output token."""
        return self.amount_in if self.is_target_amount else None

class TransferCommand(BaseModel):
    """A command to transfer tokens."""
    action: Literal["transfer"]
    amount: float
    token: Union[str, Dict[str, Any]]  # Token symbol or token info dict
    recipient: str  # Recipient address or ENS name
    natural_command: Optional[str] = None  # The original command text
    metadata: Optional[Dict[str, Any]] = None

class BridgeCommand(BaseModel):
    """A command to bridge tokens across chains."""
    action: Literal["bridge"]
    amount: float
    token: Union[str, Dict[str, Any]]  # Token symbol or token info dict
    from_chain_id: int  # Source chain ID
    to_chain_id: int  # Destination chain ID
    natural_command: Optional[str] = None  # The original command text
    metadata: Optional[Dict[str, Any]] = None

class BalanceCommand(BaseModel):
    """A command to check token balances."""
    action: Literal["balance"]
    token: Optional[str] = None  # Token symbol (optional)
    chain_id: Optional[int] = None  # Chain ID (optional)
    natural_command: Optional[str] = None  # The original command text
    metadata: Optional[Dict[str, Any]] = None

class BaseCommand(BaseModel):
    """Base class for all commands."""
    action: str
    natural_command: Optional[str] = None
