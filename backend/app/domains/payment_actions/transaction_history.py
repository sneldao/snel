"""Payment transaction history tracking."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class TransactionStatus(Enum):
    """Status of executed payment transaction."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentTransaction(BaseModel):
    """Record of an executed payment action."""
    id: str = Field(description="Unique transaction ID")
    wallet_address: str = Field(description="User's wallet address")
    action_id: str = Field(description="Associated payment action ID")
    action_name: str = Field(description="Payment action name")
    
    # Transaction details
    status: TransactionStatus = Field(description="Current transaction status")
    ticket_id: str = Field(description="MNEE ticket ID for tracking")
    transaction_hash: Optional[str] = Field(default=None, description="On-chain transaction hash")
    
    # Payment details
    from_address: str = Field(description="Sender wallet address")
    to_address: str = Field(description="Recipient wallet address")
    amount: str = Field(description="Amount transferred")
    token: str = Field(description="Token symbol")
    fee: Optional[str] = Field(default=None, description="Transaction fee")
    chain_id: int = Field(description="Chain ID where transaction occurred")
    
    # Timestamps
    created_at: datetime = Field(description="When transaction was submitted")
    confirmed_at: Optional[datetime] = Field(default=None, description="When transaction confirmed")
    updated_at: datetime = Field(description="Last status update")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class TransactionHistoryService:
    """Manages payment transaction history (in-memory for now, ready for persistence)."""
    
    def __init__(self):
        """Initialize history storage."""
        # Structure: {wallet_address: {transaction_id: PaymentTransaction}}
        self._history: Dict[str, Dict[str, PaymentTransaction]] = {}
    
    async def record_transaction(
        self,
        wallet_address: str,
        transaction: PaymentTransaction,
    ) -> PaymentTransaction:
        """Record a new transaction in history."""
        if wallet_address not in self._history:
            self._history[wallet_address] = {}
        
        self._history[wallet_address][transaction.id] = transaction
        return transaction
    
    async def get_transaction(
        self,
        wallet_address: str,
        transaction_id: str,
    ) -> Optional[PaymentTransaction]:
        """Get a specific transaction."""
        return self._history.get(wallet_address, {}).get(transaction_id)
    
    async def get_transaction_by_ticket(
        self,
        wallet_address: str,
        ticket_id: str,
    ) -> Optional[PaymentTransaction]:
        """Get transaction by MNEE ticket ID."""
        user_txns = self._history.get(wallet_address, {})
        for txn in user_txns.values():
            if txn.ticket_id == ticket_id:
                return txn
        return None
    
    async def get_transactions(
        self,
        wallet_address: str,
        status: Optional[TransactionStatus] = None,
        limit: int = 50,
    ) -> List[PaymentTransaction]:
        """Get user's transaction history."""
        user_txns = list(self._history.get(wallet_address, {}).values())
        
        # Filter by status if provided
        if status:
            user_txns = [t for t in user_txns if t.status == status]
        
        # Sort by created_at descending (newest first)
        user_txns.sort(key=lambda t: t.created_at, reverse=True)
        
        return user_txns[:limit]
    
    async def update_transaction_status(
        self,
        wallet_address: str,
        transaction_id: str,
        status: TransactionStatus,
        transaction_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[PaymentTransaction]:
        """Update transaction status (e.g., when MNEE API confirms)."""
        txn = await self.get_transaction(wallet_address, transaction_id)
        if not txn:
            return None
        
        # Update status
        txn.status = status
        txn.updated_at = datetime.utcnow()
        
        # Update transaction hash if provided
        if transaction_hash:
            txn.transaction_hash = transaction_hash
        
        # Update timestamp if confirmed
        if status == TransactionStatus.CONFIRMED and not txn.confirmed_at:
            txn.confirmed_at = datetime.utcnow()
        
        # Merge metadata
        if metadata:
            txn.metadata.update(metadata)
        
        return txn
    
    async def get_action_execution_count(
        self,
        wallet_address: str,
        action_id: str,
    ) -> int:
        """Get number of times an action has been executed."""
        user_txns = self._history.get(wallet_address, {}).values()
        return sum(1 for t in user_txns if t.action_id == action_id and t.status != TransactionStatus.FAILED)
    
    async def get_recent_transactions(
        self,
        wallet_address: str,
        days: int = 7,
    ) -> List[PaymentTransaction]:
        """Get transactions from last N days."""
        from datetime import timedelta
        
        user_txns = list(self._history.get(wallet_address, {}).values())
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent = [t for t in user_txns if t.created_at >= cutoff]
        recent.sort(key=lambda t: t.created_at, reverse=True)
        
        return recent


# Singleton instance
_history_service: Optional[TransactionHistoryService] = None


async def get_transaction_history_service() -> TransactionHistoryService:
    """Get or create singleton history service."""
    global _history_service
    if _history_service is None:
        _history_service = TransactionHistoryService()
    return _history_service
