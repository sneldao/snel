"""
Base protocol interface for swap protocols.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal

class SwapProtocol(ABC):
    """Base class for swap protocols."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Protocol name."""
        pass

    @abstractmethod
    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Get a quote for a swap."""
        pass

    @abstractmethod
    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Build a transaction from a quote."""
        pass

    @abstractmethod
    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        pass

    @abstractmethod
    async def get_token_info(
        self,
        token_address: str,
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token information (decimals, symbol, etc.)."""
        pass 