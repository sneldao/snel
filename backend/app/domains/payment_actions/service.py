"""Payment action service - core business logic for managing user actions."""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import (
    PaymentAction,
    PaymentActionType,
    CreatePaymentActionRequest,
    UpdatePaymentActionRequest,
)
from .storage import BaseStorageBackend, InMemoryStorageBackend


class PaymentActionService:
    """
    Payment action service with pluggable storage backends.
    
    ENHANCEMENT FIRST: Uses pluggable storage (in-memory, Redis, PostgreSQL).
    MODULAR: Storage abstraction allows switching backends without changing logic.
    PERFORMANT: Redis backend enables distributed, cached access.
    """

    def __init__(self, backend: Optional[BaseStorageBackend] = None):
        """Initialize with storage backend (defaults to in-memory)."""
        self._backend = backend or InMemoryStorageBackend()
        
    async def create_action(
        self,
        wallet_address: str,
        request: CreatePaymentActionRequest,
    ) -> PaymentAction:
        """Create a new payment action for user."""
        action_id = f"action_{uuid.uuid4().hex[:12]}"
        
        action = PaymentAction(
            id=action_id,
            wallet_address=wallet_address,
            name=request.name,
            action_type=request.action_type,
            recipient_address=request.recipient_address,
            amount=request.amount,
            token=request.token,
            chain_id=request.chain_id,
            schedule=request.schedule,
            triggers=request.triggers or [],
            is_pinned=request.is_pinned,
            metadata=request.metadata or {},
            created_at=datetime.utcnow(),
        )
        
        # Store via backend
        await self._backend.create(wallet_address, action_id, action)
        return action
    
    async def get_action(
        self,
        wallet_address: str,
        action_id: str,
    ) -> Optional[PaymentAction]:
        """Retrieve a specific action."""
        return await self._backend.get(wallet_address, action_id)
    
    async def get_actions(
        self,
        wallet_address: str,
        action_type: Optional[PaymentActionType] = None,
        enabled_only: bool = False,
        pinned_only: bool = False,
    ) -> List[PaymentAction]:
        """Retrieve user's actions with optional filtering."""
        user_actions = await self._backend.list(wallet_address)
        
        # Apply filters
        filtered = list(user_actions)
        
        if action_type:
            filtered = [a for a in filtered if a.action_type == action_type]
        
        if enabled_only:
            filtered = [a for a in filtered if a.is_enabled]
        
        if pinned_only:
            filtered = [a for a in filtered if a.is_pinned]
        
        # Sort by order, then by creation date
        filtered.sort(key=lambda a: (a.order, a.created_at))
        
        return filtered
    
    async def update_action(
        self,
        wallet_address: str,
        action_id: str,
        request: UpdatePaymentActionRequest,
    ) -> Optional[PaymentAction]:
        """Update an existing action."""
        action = await self.get_action(wallet_address, action_id)
        if not action:
            return None
        
        # Apply updates (CLEAN: only update provided fields)
        update_data = request.model_dump(exclude_unset=True)
        updated = action.model_copy(update={
            **update_data,
            'last_used': action.last_used,  # Preserve unless explicitly set
        })
        
        # Store updated action via backend
        await self._backend.update(wallet_address, action_id, updated)
        return updated
    
    async def delete_action(
        self,
        wallet_address: str,
        action_id: str,
    ) -> bool:
        """Delete an action."""
        return await self._backend.delete(wallet_address, action_id)
    
    async def mark_used(
        self,
        wallet_address: str,
        action_id: str,
    ) -> Optional[PaymentAction]:
        """Mark action as used (increment counter, update timestamp)."""
        action = await self.get_action(wallet_address, action_id)
        if not action:
            return None
        
        updated = action.model_copy(update={
            'last_used': datetime.utcnow(),
            'usage_count': action.usage_count + 1,
        })
        
        await self._backend.update(wallet_address, action_id, updated)
        return updated
    
    async def get_quick_actions(
        self,
        wallet_address: str,
    ) -> List[PaymentAction]:
        """Get pinned quick action buttons for user (max 5 most recently used)."""
        pinned = await self.get_actions(wallet_address, pinned_only=True)
        
        # Return pinned actions sorted by order, then by last used
        pinned.sort(key=lambda a: (a.order, a.last_used or a.created_at), reverse=True)
        
        return pinned[:5]
    
    async def export_actions(
        self,
        wallet_address: str,
    ) -> List[PaymentAction]:
        """Export all user actions (for backup/migration)."""
        return await self.get_actions(wallet_address)
    
    async def get_all_wallets(self) -> List[str]:
        """Get all wallets that have payment actions (for keeper jobs)."""
        return await self._backend.list_wallets()


# Singleton instance
_service_instance: Optional[PaymentActionService] = None


async def get_payment_action_service() -> PaymentActionService:
    """
    Get or create singleton service instance.
    
    MODULAR: Always uses configured storage backend from environment.
    """
    global _service_instance
    if _service_instance is None:
        # Import here to avoid circular imports
        # Default to Persistent JSON Storage for Hackathon/Dev
        from .storage import JsonFileStorageBackend
        import os
        
        # Use a path in the project root or temp dir to persist
        storage_path = os.getenv("PAYMENT_STORAGE_PATH", "payment_actions_db.json")
        backend = JsonFileStorageBackend(file_path=storage_path)
        _service_instance = PaymentActionService(backend=backend)
    
    return _service_instance
