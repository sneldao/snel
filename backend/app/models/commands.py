"""
API request and response models.
"""
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class BridgeRequest(BaseModel):
    """Request to bridge tokens across chains."""
    from_token: str = Field(description="Source token symbol or address")
    to_token: str = Field(description="Destination token symbol or address")
    amount: Decimal = Field(description="Amount to bridge")
    from_chain_id: int = Field(description="Source chain ID")
    to_chain_id: int = Field(description="Destination chain ID")
    wallet_address: str = Field(description="Wallet address")

class BridgeQuoteResponse(BaseModel):
    """Response containing bridge quote information."""
    quote_id: str
    from_token: str
    to_token: str
    from_amount: Decimal
    to_amount: Decimal
    from_chain_id: int
    to_chain_id: int
    fee_amount: Decimal
    fee_token: str
    expiry: int
    
class BridgeExecuteResponse(BaseModel):
    """Response after executing a bridge transaction."""
    transaction_hash: str
    from_chain_id: int
    to_chain_id: int
    status: str
    estimated_time: Optional[int] = Field(default=None)

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
