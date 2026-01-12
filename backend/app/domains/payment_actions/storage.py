"""Storage backends for payment actions - abstraction for Redis and PostgreSQL."""
import json
import redis.asyncio as redis
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from .models import PaymentAction


class BaseStorageBackend(ABC):
    """Abstract base for storage backends (CLEAN: single interface for all backends)."""
    
    @abstractmethod
    async def create(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Store a new action."""
        pass
    
    @abstractmethod
    async def get(self, wallet_address: str, action_id: str) -> Optional[PaymentAction]:
        """Retrieve a single action."""
        pass
    
    @abstractmethod
    async def list(self, wallet_address: str) -> List[PaymentAction]:
        """List all actions for a user."""
        pass
    
    @abstractmethod
    async def update(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Update an action."""
        pass
    
    @abstractmethod
    async def delete(self, wallet_address: str, action_id: str) -> bool:
        """Delete an action."""
        pass
    
    @abstractmethod
    async def delete_all(self, wallet_address: str) -> int:
        """Delete all actions for a user (cleanup)."""
        pass
    
    @abstractmethod
    async def list_wallets(self) -> List[str]:
        """List all wallets that have payment actions."""
        pass


class InMemoryStorageBackend(BaseStorageBackend):
    """In-memory storage backend (for testing/dev)."""
    
    def __init__(self):
        """Initialize with empty store."""
        self._store: Dict[str, Dict[str, PaymentAction]] = {}
    
    async def create(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Store a new action."""
        if wallet_address not in self._store:
            self._store[wallet_address] = {}
        self._store[wallet_address][action_id] = action
    
    async def get(self, wallet_address: str, action_id: str) -> Optional[PaymentAction]:
        """Retrieve a single action."""
        return self._store.get(wallet_address, {}).get(action_id)
    
    async def list(self, wallet_address: str) -> List[PaymentAction]:
        """List all actions for a user."""
        return list(self._store.get(wallet_address, {}).values())
    
    async def update(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Update an action."""
        if wallet_address in self._store and action_id in self._store[wallet_address]:
            self._store[wallet_address][action_id] = action
    
    async def delete(self, wallet_address: str, action_id: str) -> bool:
        """Delete an action."""
        user_actions = self._store.get(wallet_address, {})
        if action_id in user_actions:
            del user_actions[action_id]
            return True
        return False
    
    async def delete_all(self, wallet_address: str) -> int:
        """Delete all actions for a user."""
        if wallet_address in self._store:
            count = len(self._store[wallet_address])
            del self._store[wallet_address]
            return count
        return 0
    
    async def list_wallets(self) -> List[str]:
        """List all wallets that have payment actions."""
        return list(self._store.keys())


class JsonFileStorageBackend(BaseStorageBackend):
    """
    JSON File storage backend (PERSISTENT: simple persistence for demos/hackathons).
    Saves state to a local JSON file.
    """
    
    def __init__(self, file_path: str = "payment_actions.json"):
        """Initialize with file path."""
        self.file_path = file_path
        self._store: Dict[str, Dict[str, PaymentAction]] = {}
        self._load()
    
    def _load(self):
        """Load data from JSON file."""
        import os
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    # Reconstruct objects
                    for wallet, actions in data.items():
                        self._store[wallet] = {}
                        for action_id, action_data in actions.items():
                            self._store[wallet][action_id] = PaymentAction(**action_data)
            except Exception as e:
                print(f"Error loading payment actions: {e}")
                self._store = {}
    
    def _save(self):
        """Save data to JSON file."""
        try:
            # Convert objects to dicts
            data = {}
            for wallet, actions in self._store.items():
                data[wallet] = {}
                for action_id, action in actions.items():
                    data[wallet][action_id] = action.model_dump(mode='json')
            
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving payment actions: {e}")

    async def create(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Store a new action."""
        if wallet_address not in self._store:
            self._store[wallet_address] = {}
        self._store[wallet_address][action_id] = action
        self._save()
    
    async def get(self, wallet_address: str, action_id: str) -> Optional[PaymentAction]:
        """Retrieve a single action."""
        return self._store.get(wallet_address, {}).get(action_id)
    
    async def list(self, wallet_address: str) -> List[PaymentAction]:
        """List all actions for a user."""
        return list(self._store.get(wallet_address, {}).values())
    
    async def update(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Update an action."""
        if wallet_address in self._store and action_id in self._store[wallet_address]:
            self._store[wallet_address][action_id] = action
            self._save()
    
    async def delete(self, wallet_address: str, action_id: str) -> bool:
        """Delete an action."""
        user_actions = self._store.get(wallet_address, {})
        if action_id in user_actions:
            del user_actions[action_id]
            self._save()
            return True
        return False
    
    async def delete_all(self, wallet_address: str) -> int:
        """Delete all actions for a user."""
        if wallet_address in self._store:
            count = len(self._store[wallet_address])
            del self._store[wallet_address]
            self._save()
            return count
        return 0
    
    async def list_wallets(self) -> List[str]:
        """List all wallets that have payment actions."""
        return list(self._store.keys())


class RedisStorageBackend(BaseStorageBackend):
    """
    Redis storage backend (PERFORMANT: fast, distributed-ready).
    Key structure: payment_actions:{wallet_address}:{action_id}
    """
    
    def __init__(self, redis_client: redis.Redis):
        """Initialize with redis client."""
        self.redis = redis_client
        self._prefix = "payment_actions"
    
    def _key(self, wallet_address: str, action_id: Optional[str] = None) -> str:
        """Generate Redis key."""
        if action_id:
            return f"{self._prefix}:{wallet_address}:{action_id}"
        return f"{self._prefix}:{wallet_address}"
    
    def _index_key(self, wallet_address: str) -> str:
        """Generate index key for listing."""
        return f"{self._prefix}:{wallet_address}:index"
    
    async def create(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Store a new action."""
        key = self._key(wallet_address, action_id)
        data = action.json()
        await self.redis.set(key, data)
        # Add to user's index for efficient listing
        await self.redis.sadd(self._index_key(wallet_address), action_id)
    
    async def get(self, wallet_address: str, action_id: str) -> Optional[PaymentAction]:
        """Retrieve a single action."""
        key = self._key(wallet_address, action_id)
        data = await self.redis.get(key)
        if data:
            return PaymentAction.parse_raw(data)
        return None
    
    async def list(self, wallet_address: str) -> List[PaymentAction]:
        """List all actions for a user."""
        index_key = self._index_key(wallet_address)
        action_ids = await self.redis.smembers(index_key)
        
        actions = []
        for action_id in action_ids:
            action = await self.get(wallet_address, action_id.decode() if isinstance(action_id, bytes) else action_id)
            if action:
                actions.append(action)
        
        return actions
    
    async def update(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Update an action."""
        key = self._key(wallet_address, action_id)
        data = action.json()
        await self.redis.set(key, data)
    
    async def delete(self, wallet_address: str, action_id: str) -> bool:
        """Delete an action."""
        key = self._key(wallet_address, action_id)
        index_key = self._index_key(wallet_address)
        
        result = await self.redis.delete(key)
        await self.redis.srem(index_key, action_id)
        
        return result > 0
    
    async def delete_all(self, wallet_address: str) -> int:
        """Delete all actions for a user."""
        index_key = self._index_key(wallet_address)
        action_ids = await self.redis.smembers(index_key)
        
        count = 0
        for action_id in action_ids:
            action_id_str = action_id.decode() if isinstance(action_id, bytes) else action_id
            key = self._key(wallet_address, action_id_str)
            await self.redis.delete(key)
            count += 1
        
        await self.redis.delete(index_key)
        return count
    
    async def list_wallets(self) -> List[str]:
        """List all wallets that have payment actions."""
        # Scan for all keys matching pattern payment_actions:{wallet}:index
        pattern = f"{self._prefix}:*:index"
        wallets = set()
        
        async for key in self.redis.scan_iter(match=pattern):
            # Extract wallet address from key pattern payment_actions:{wallet}:index
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.split(":")
            if len(parts) == 3:
                wallets.add(parts[1])
        
        return list(wallets)


class PostgreSQLStorageBackend(BaseStorageBackend):
    """
    PostgreSQL storage backend (fallback for production).
    Requires: sqlalchemy async driver, migration needed.
    """
    
    def __init__(self, session_factory):
        """Initialize with SQLAlchemy async session factory."""
        self.session_factory = session_factory
    
    async def create(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Store a new action."""
        # TODO: Implement with SQLAlchemy ORM
        # INSERT INTO payment_actions VALUES (...)
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
    
    async def get(self, wallet_address: str, action_id: str) -> Optional[PaymentAction]:
        """Retrieve a single action."""
        # TODO: SELECT * FROM payment_actions WHERE action_id = ?
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
    
    async def list(self, wallet_address: str) -> List[PaymentAction]:
        """List all actions for a user."""
        # TODO: SELECT * FROM payment_actions WHERE wallet_address = ?
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
    
    async def update(self, wallet_address: str, action_id: str, action: PaymentAction) -> None:
        """Update an action."""
        # TODO: UPDATE payment_actions SET ... WHERE action_id = ?
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
    
    async def delete(self, wallet_address: str, action_id: str) -> bool:
        """Delete an action."""
        # TODO: DELETE FROM payment_actions WHERE action_id = ?
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
    
    async def delete_all(self, wallet_address: str) -> int:
        """Delete all actions for a user."""
        # TODO: DELETE FROM payment_actions WHERE wallet_address = ?
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
    
    async def list_wallets(self) -> List[str]:
        """List all wallets that have payment actions."""
        # TODO: SELECT DISTINCT wallet_address FROM payment_actions
        raise NotImplementedError("PostgreSQL backend requires ORM setup")
