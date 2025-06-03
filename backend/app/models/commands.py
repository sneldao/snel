"""
API request and response models for legacy endpoints.
Note: Bridge models removed - bridges now handled by unified chat processor.
"""
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class BalanceRequest(BaseModel):
    """Request to check token balance."""
    wallet_address: str = Field(description="Wallet address")
    chain_id: int = Field(description="Chain ID")
    token_address: Optional[str] = Field(default=None, description="Token address (optional)")

class TokenBalance(BaseModel):
    """Token balance information."""
    token_symbol: str
    token_address: str
    balance: Decimal
    usd_value: Optional[Decimal] = Field(default=None)

class BalanceResponse(BaseModel):
    """Response containing token balances."""
    wallet_address: str
    chain_id: int
    balances: list[TokenBalance]

class TransactionStatus(BaseModel):
    """Transaction status information."""
    transaction_hash: str
    status: str
    chain_id: int
    block_number: Optional[int] = Field(default=None)
    confirmations: Optional[int] = Field(default=None)
    error: Optional[str] = Field(default=None)
