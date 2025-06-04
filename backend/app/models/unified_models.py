"""
Unified models for consistent command processing across the application.
"""
from typing import Dict, Any, Optional, Union, List
from enum import Enum
from pydantic import BaseModel, Field


class CommandType(Enum):
    """Supported command types."""
    TRANSFER = "transfer"
    BRIDGE = "bridge"
    SWAP = "swap"
    BALANCE = "balance"
    PORTFOLIO = "portfolio"
    PROTOCOL_RESEARCH = "protocol_research"
    CONTEXTUAL_QUESTION = "contextual_question"
    GREETING = "greeting"
    CONFIRMATION = "confirmation"
    UNKNOWN = "unknown"


class TransactionStatus(Enum):
    """Transaction status types."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(Enum):
    """Agent types for consistent response handling."""
    TRANSFER = "transfer"
    BRIDGE = "bridge"
    SWAP = "swap"
    BALANCE = "balance"
    PORTFOLIO = "portfolio"
    PROTOCOL_RESEARCH = "protocol_research"
    DEFAULT = "default"
    ERROR = "error"


class TokenInfo(BaseModel):
    """Standardized token information model."""
    symbol: str = Field(description="Token symbol (e.g., ETH, USDC)")
    address: Optional[str] = Field(default=None, description="Token contract address")
    decimals: int = Field(default=18, description="Token decimals")
    name: Optional[str] = Field(default=None, description="Token full name")
    logo_uri: Optional[str] = Field(default=None, description="Token logo URL")
    price_usd: Optional[float] = Field(default=None, description="Token price in USD")
    verified: bool = Field(default=True, description="Whether token is verified")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional token metadata")


class TransactionData(BaseModel):
    """Standardized transaction data model."""
    to: str = Field(description="Transaction recipient address")
    data: Optional[str] = Field(default=None, description="Transaction data")
    value: str = Field(default="0", description="Transaction value in wei")
    gas_limit: Optional[str] = Field(default=None, description="Gas limit")
    gas_price: Optional[str] = Field(default=None, description="Gas price")
    chain_id: int = Field(description="Chain ID")
    from_address: Optional[str] = Field(default=None, description="Sender address")


class CommandDetails(BaseModel):
    """Parsed command details."""
    amount: Optional[float] = Field(default=None, description="Transaction amount")
    token_in: Optional[TokenInfo] = Field(default=None, description="Input token")
    token_out: Optional[TokenInfo] = Field(default=None, description="Output token")
    destination: Optional[str] = Field(default=None, description="Destination address or ENS")
    source_chain: Optional[str] = Field(default=None, description="Source chain name")
    destination_chain: Optional[str] = Field(default=None, description="Destination chain name")
    protocol: Optional[str] = Field(default=None, description="Protocol name")
    additional_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")


class UnifiedCommand(BaseModel):
    """Unified command model for all command types."""
    command: str = Field(description="Original command string")
    command_type: CommandType = Field(description="Detected command type")
    wallet_address: Optional[str] = Field(default=None, description="User wallet address")
    chain_id: Optional[int] = Field(default=None, description="Current chain ID")
    user_name: Optional[str] = Field(default=None, description="User name")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    details: Optional[CommandDetails] = Field(default=None, description="Parsed command details")


class ResponseContent(BaseModel):
    """Standardized response content model."""
    message: str = Field(description="Main response message")
    type: str = Field(description="Response type (e.g., confirmation, result, error)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested actions")
    protocols_tried: Optional[List[str]] = Field(default=None, description="Protocols attempted")


class UnifiedResponse(BaseModel):
    """Unified response model for all command types."""
    content: Union[str, Dict[str, Any], ResponseContent] = Field(description="Response content")
    agent_type: AgentType = Field(description="Agent type that processed the command")
    status: str = Field(default="success", description="Response status (success/error)")
    awaiting_confirmation: bool = Field(default=False, description="Whether confirmation is needed")
    transaction: Optional[TransactionData] = Field(default=None, description="Transaction data if applicable")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    error: Optional[str] = Field(default=None, description="Error message if any")


class ValidationResult(BaseModel):
    """Command validation result."""
    is_valid: bool = Field(description="Whether the command is valid")
    error_message: Optional[str] = Field(default=None, description="Error message if invalid")
    missing_requirements: Optional[List[str]] = Field(default=None, description="Missing requirements")


class ProcessingContext(BaseModel):
    """Context for command processing."""
    wallet_connected: bool = Field(default=False, description="Whether wallet is connected")
    chain_supported: bool = Field(default=False, description="Whether chain is supported")
    api_keys_available: Dict[str, bool] = Field(default_factory=dict, description="Available API keys")
    user_preferences: Optional[Dict[str, Any]] = Field(default=None, description="User preferences")


# Legacy compatibility models for existing endpoints
class ChatCommand(BaseModel):
    """Legacy chat command model for backward compatibility."""
    command: str = Field(description="Chat command string")
    wallet_address: Optional[str] = Field(default=None, description="User wallet address")
    chain_id: Optional[int] = Field(default=None, description="Current chain ID")
    user_name: Optional[str] = Field(default=None, description="User name")
    openai_api_key: Optional[str] = Field(default=None, description="User-supplied OpenAI API key")


class ChatResponse(BaseModel):
    """Legacy chat response model for backward compatibility."""
    content: Union[str, Dict[str, Any]]
    agent_type: Optional[str] = Field(default="default")
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    awaiting_confirmation: Optional[bool] = Field(default=False)
    status: Optional[str] = Field(default="success")
    error: Optional[str] = Field(default=None)
    transaction: Optional[Dict[str, Any]] = Field(default=None)
