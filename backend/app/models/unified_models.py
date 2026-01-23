"""
Unified models for consistent command processing across the application.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

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
    GMP_OPERATION = "gmp_operation"  # General Message Passing operations
    CROSS_CHAIN_SWAP = "cross_chain_swap"  # Advanced cross-chain swaps
    TRANSACTION_STEP_COMPLETE = (
        "transaction_step_complete"  # Multi-step transaction management
    )
    BRIDGE_TO_PRIVACY = "bridge_to_privacy"  # Bridge to privacy chain (Zcash)
    SET_PRIVACY_DEFAULT = "set_privacy_default"  # Set default privacy level
    OVERRIDE_PRIVACY = "override_privacy"  # Override privacy for specific transaction
    X402_PRIVACY = "x402_privacy"  # x402 programmatic privacy transaction
    X402_PAYMENT = "x402_payment"  # x402 agentic payment operations
    PAYMENT_ACTION = (
        "payment_action"  # User payment action management (create/update/delete)
    )
    UNKNOWN = "unknown"


class TransactionStatus(Enum):
    """Transaction status types."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PrivacyLevel(Enum):
    """Privacy levels for transactions."""

    PUBLIC = "public"
    PRIVATE = "private"
    COMPLIANCE = "compliance"


class AgentType(Enum):
    """Agent types for consistent response handling."""

    TRANSFER = "transfer"
    BRIDGE = "bridge"
    SWAP = "swap"
    BALANCE = "balance"
    PORTFOLIO = "portfolio"
    PROTOCOL_RESEARCH = "protocol_research"
    GMP_OPERATION = "gmp_operation"
    CROSS_CHAIN_SWAP = "cross_chain_swap"
    BRIDGE_TO_PRIVACY = "bridge_to_privacy"
    PAYMENT = "payment"
    DEFAULT = "default"
    ERROR = "error"


class ChainPrivacyRoute(BaseModel):
    """Privacy route information for chain-aware privacy transactions."""

    method: str = Field(
        ..., description="Privacy method (x402_privacy, gmp_privacy, direct_zcash)"
    )
    privacy_level: PrivacyLevel = Field(..., description="Privacy level")
    estimated_latency: str = Field(..., description="Estimated transaction latency")
    capabilities: dict[str, bool] = Field(..., description="Route capabilities")


class TokenInfo(BaseModel):
    """Standardized token information model."""

    symbol: str = Field(description="Token symbol (e.g., ETH, USDC)")
    address: str | None = Field(default=None, description="Token contract address")
    decimals: int = Field(default=18, description="Token decimals")
    name: str | None = Field(default=None, description="Token full name")
    logo_uri: str | None = Field(default=None, description="Token logo URL")
    price_usd: float | None = Field(default=None, description="Token price in USD")
    verified: bool = Field(default=True, description="Whether token is verified")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional token metadata"
    )


class TransactionData(BaseModel):
    """Standardized transaction data model."""

    to: str = Field(description="Transaction recipient address")
    data: str | None = Field(default="0x", description="Transaction data")
    value: str = Field(default="0", description="Transaction value in wei")
    gasLimit: str | None = Field(
        default=None, alias="gas_limit", description="Gas limit"
    )
    gasPrice: str | None = Field(
        default=None, alias="gas_price", description="Gas price"
    )
    chainId: int = Field(alias="chain_id", description="Chain ID")
    from_address: str | None = Field(default=None, description="Sender address")

    class Config:
        validate_by_name: bool = True


class CommandDetails(BaseModel):
    """Parsed command details."""

    class Config:
        extra: str = "allow"

    amount: float | None = Field(default=None, description="Transaction amount")
    token_in: TokenInfo | None = Field(default=None, description="Input token")
    token_out: TokenInfo | None = Field(default=None, description="Output token")
    destination: str | None = Field(
        default=None, description="Destination address or ENS"
    )
    source_chain: str | None = Field(default=None, description="Source chain name")
    destination_chain: str | None = Field(
        default=None, description="Destination chain name"
    )
    protocol: str | None = Field(default=None, description="Protocol name")
    is_usd_amount: bool | None = Field(
        default=False, description="Whether the amount is specified in USD"
    )
    # Multi-step/Transaction completion fields
    wallet_address: str | None = Field(default=None, description="Wallet address")
    tx_hash: str | None = Field(default=None, description="Transaction hash")
    chain_id: int | None = Field(default=None, description="Chain ID")
    success: bool | None = Field(default=True, description="Transaction success status")
    additional_params: dict[str, Any] | None = Field(
        default_factory=dict, description="Additional parameters"
    )


class UnifiedCommand(BaseModel):
    """Unified command model for all command types."""

    command: str = Field(description="Original command string")
    command_type: CommandType = Field(description="Detected command type")
    wallet_address: str | None = Field(default=None, description="User wallet address")
    chain_id: int | None = Field(default=None, description="Current chain ID")
    user_name: str | None = Field(default=None, description="User name")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    details: CommandDetails | None = Field(
        default=None, description="Parsed command details"
    )
    research_mode: str | None = Field(
        default="quick", description="Research mode for protocol research (quick|deep)"
    )

    @property
    def original_text(self) -> str:
        """Alias for command field to maintain compatibility."""
        return self.command


class ResponseContent(BaseModel):
    """Standardized response content model."""

    message: str = Field(description="Main response message")
    type: str = Field(description="Response type (e.g., confirmation, result, error)")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional details"
    )
    suggestions: list[str] | None = Field(default=None, description="Suggested actions")
    protocols_tried: list[str] | None = Field(
        default=None, description="Protocols attempted"
    )


class UnifiedResponse(BaseModel):
    """Unified response model for all command types."""

    content: str | dict[str, Any] | ResponseContent = Field(
        description="Response content"
    )
    agent_type: AgentType = Field(description="Agent type that processed the command")
    status: str = Field(
        default="success", description="Response status (success/error)"
    )
    awaiting_confirmation: bool = Field(
        default=False, description="Whether confirmation is needed"
    )
    transaction: TransactionData | None = Field(
        default=None, description="Transaction data if applicable"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )
    error: str | None = Field(default=None, description="Error message if any")


class ValidationResult(BaseModel):
    """Command validation result."""

    is_valid: bool = Field(description="Whether the command is valid")
    error_message: str | None = Field(
        default=None, description="Error message if invalid"
    )
    missing_requirements: list[str] | None = Field(
        default=None, description="Missing requirements"
    )


class ProcessingContext(BaseModel):
    """Context for command processing."""

    wallet_connected: bool = Field(
        default=False, description="Whether wallet is connected"
    )
    chain_supported: bool = Field(
        default=False, description="Whether chain is supported"
    )
    api_keys_available: dict[str, bool] = Field(
        default_factory=dict, description="Available API keys"
    )
    user_preferences: dict[str, Any] | None = Field(
        default=None, description="User preferences"
    )


# Legacy compatibility models for existing endpoints
class ChatCommand(BaseModel):
    """Legacy chat command model for backward compatibility."""

    command: str = Field(description="Chat command string")
    wallet_address: str | None = Field(default=None, description="User wallet address")
    chain_id: int | None = Field(default=None, description="Current chain ID")
    user_name: str | None = Field(default=None, description="User name")
    openai_api_key: str | None = Field(
        default=None, description="User-supplied OpenAI API key"
    )


class TransactionStepCompletion(BaseModel):
    """Model for transaction step completion data."""

    wallet_address: str = Field(description="User wallet address")
    chain_id: int = Field(description="Current chain ID")
    tx_hash: str = Field(description="Transaction hash")
    success: bool = Field(
        default=True, description="Whether the transaction was successful"
    )
    error: str | None = Field(
        default=None, description="Error message if transaction failed"
    )


class ChatResponse(BaseModel):
    """Legacy chat response model for backward compatibility."""

    content: str | dict[str, Any]
    agent_type: str | None = Field(default="default")
    metadata: dict[str, Any] | None = Field(default=None)
    awaiting_confirmation: bool | None = Field(default=False)
    status: str | None = Field(default="success")
    error: str | None = Field(default=None)
    transaction: dict[str, Any] | None = Field(default=None)
