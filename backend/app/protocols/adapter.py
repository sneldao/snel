"""
Protocol adapter interface for standardizing interactions with swap protocols.
"""
from typing import Dict, Any, Optional, Protocol, List
from decimal import Decimal
from app.models.token import TokenInfo


class ProtocolAdapter(Protocol):
    """Protocol adapter interface for swap protocols."""
    
    @property
    def protocol_id(self) -> str:
        """Unique protocol identifier."""
        ...
    
    @property
    def name(self) -> str:
        """Human-readable protocol name."""
        ...
    
    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        ...
    
    def is_supported(self, chain_id: int) -> bool:
        """Check if protocol supports a specific chain."""
        return chain_id in self.supported_chains
    
    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """
        Get a quote for swapping tokens.
        
        Args:
            from_token: Source token info
            to_token: Destination token info
            amount: Amount to swap
            chain_id: Chain ID to use
            wallet_address: User's wallet address
            
        Returns:
            Standardized quote response
        """
        ...
    
    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """
        Build a transaction from a quote.
        
        Args:
            quote: Quote from get_quote
            chain_id: Chain ID to use
            wallet_address: User's wallet address
            
        Returns:
            Transaction data ready for execution
        """
        ...
    
    async def close(self):
        """Close any resources used by this adapter."""
        pass 