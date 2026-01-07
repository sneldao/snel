"""Payment action models - unified schema for all user payment actions."""
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class PaymentActionType(Enum):
    """Types of payment actions users can create."""
    SEND = "send"  # Simple send to address
    RECURRING = "recurring"  # Recurring/scheduled payments
    TEMPLATE = "template"  # Reusable payment template
    SHORTCUT = "shortcut"  # Natural language shortcut


class PaymentActionFrequency(Enum):
    """Frequency options for recurring payments."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PaymentActionSchedule(BaseModel):
    """Schedule configuration for recurring payments."""
    frequency: PaymentActionFrequency
    day_of_week: Optional[int] = Field(
        default=None, 
        ge=0, 
        le=6,
        description="0=Sunday, 6=Saturday (for weekly)"
    )
    day_of_month: Optional[int] = Field(
        default=None,
        ge=1,
        le=31,
        description="Day of month (for monthly)"
    )


class PaymentRecipient(BaseModel):
    """Recipient for batch payment with amount or percentage split."""
    address: str = Field(description="Recipient wallet address")
    amount: Optional[str] = Field(default=None, description="Fixed amount to send")
    percentage: Optional[float] = Field(default=None, description="Percentage of total to send (0-100)")
    label: Optional[str] = Field(default=None, description="Human-readable label (e.g., 'Creator A')")


class PaymentAction(BaseModel):
    """Unified model for all user payment actions."""
    id: str = Field(description="Unique action ID")
    wallet_address: str = Field(description="User's wallet address")
    
    # Core action data
    name: str = Field(description="User-friendly name (e.g., 'Weekly Rent')")
    action_type: PaymentActionType = Field(description="Type of action")
    
    # Payment details
    recipient_address: Optional[str] = Field(default=None, description="Recipient wallet address (single payment)")
    amount: str = Field(description="Amount to send")
    token: str = Field(description="Token symbol (ETH, USDC, MNEE, etc.)")
    chain_id: int = Field(description="Chain ID for transaction")
    
    # Batch payment support
    recipients: Optional[List[PaymentRecipient]] = Field(
        default=None,
        description="Multiple recipients for batch payments with splits"
    )
    
    # Optional: Recurring configuration
    schedule: Optional[PaymentActionSchedule] = Field(
        default=None,
        description="Schedule info for recurring actions"
    )
    
    # Optional: Natural language triggers for shortcuts
    triggers: Optional[List[str]] = Field(
        default_factory=list,
        description="Natural language triggers (e.g., ['weekly coffee', 'rent time'])"
    )
    
    # Metadata
    created_at: datetime = Field(description="When action was created")
    last_used: Optional[datetime] = Field(
        default=None,
        description="When action was last executed"
    )
    usage_count: int = Field(default=0, description="Number of times used")
    is_enabled: bool = Field(default=True, description="Whether action is active")
    
    # Display preferences
    is_pinned: bool = Field(
        default=False,
        description="Whether to show in quick actions"
    )
    order: int = Field(
        default=0,
        description="Display order in quick actions list"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user-defined metadata"
    )


class CreatePaymentActionRequest(BaseModel):
    """Request to create a new payment action."""
    name: str
    action_type: PaymentActionType
    recipient_address: Optional[str] = None
    amount: str
    token: str
    chain_id: int
    schedule: Optional[PaymentActionSchedule] = None
    triggers: Optional[List[str]] = None
    is_pinned: bool = False
    recipients: Optional[List[PaymentRecipient]] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdatePaymentActionRequest(BaseModel):
    """Request to update an existing payment action."""
    name: Optional[str] = None
    amount: Optional[str] = None
    token: Optional[str] = None
    recipient_address: Optional[str] = None
    schedule: Optional[PaymentActionSchedule] = None
    triggers: Optional[List[str]] = None
    is_enabled: Optional[bool] = None
    is_pinned: Optional[bool] = None
    order: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentActionResponse(PaymentAction):
    """Response model for payment action queries."""
    pass


class PaymentActionListResponse(BaseModel):
    """Response for listing payment actions."""
    actions: List[PaymentActionResponse]
    total: int
    filtered: int
