"""Webhook infrastructure for AI agents to trigger payment actions programmatically."""
import logging
import hmac
import hashlib
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """Types of webhook events."""
    EXECUTE_ACTION = "execute_action"
    EXECUTE_BATCH = "execute_batch"
    CREATE_ACTION = "create_action"


class WebhookPayloadExecuteAction(BaseModel):
    """Webhook payload to execute an existing payment action."""
    action_id: str = Field(description="ID of payment action to execute")
    wallet_address: str = Field(description="Wallet executing the action")
    # Optional: override amount or recipient for flexible execution
    override_amount: Optional[str] = Field(default=None, description="Override action amount")
    override_recipient: Optional[str] = Field(default=None, description="Override action recipient")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class WebhookPayloadExecuteBatch(BaseModel):
    """Webhook payload to execute a batch payment."""
    wallet_address: str = Field(description="Wallet executing the batch")
    token: str = Field(description="Token to send (ETH, MNEE, USDC, etc.)")
    chain_id: int = Field(description="Chain ID")
    recipients: list[Dict[str, str]] = Field(
        description="List of recipients: [{address, amount}, ...]"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class WebhookRequest(BaseModel):
    """Webhook request from AI agent or external system."""
    event_type: WebhookEventType = Field(description="Type of webhook event")
    payload: Dict[str, Any] = Field(description="Event payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(description="Unique request ID for tracking")
    signature: Optional[str] = Field(default=None, description="HMAC signature for verification")


class WebhookResponse(BaseModel):
    """Response to webhook request."""
    success: bool
    request_id: str
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WebhookValidator:
    """
    Validates webhook signatures using HMAC-SHA256.
    
    Agents sign their requests with a shared secret, ensuring:
    - Requests come from authorized agents
    - Payload wasn't tampered with
    """
    
    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload.
        
        Args:
            payload: JSON string of request body
            secret: Shared secret key
        
        Returns:
            Hex-encoded HMAC signature
        """
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Original request body
            signature: Provided signature from request
            secret: Shared secret key
        
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = WebhookValidator.generate_signature(payload, secret)
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)


class WebhookExecutionRecord(BaseModel):
    """Record of webhook execution for auditing."""
    request_id: str
    event_type: WebhookEventType
    wallet_address: str
    action_id: Optional[str] = None
    ticket_id: Optional[str] = None
    status: str  # success, failed, pending
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "event_type": self.event_type.value,
            "wallet_address": self.wallet_address,
            "action_id": self.action_id,
            "ticket_id": self.ticket_id,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }
