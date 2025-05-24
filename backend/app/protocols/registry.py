"""
Protocol registry for managing multiple swap protocols.
"""
from typing import Dict, List, Optional, Any
import logging
from app.models.token import TokenInfo, token_registry
from app.services.token_service import token_service
from .brian_adapter import BrianAdapter
from .zerox_adapter import ZeroXAdapter

logger = logging.getLogger(__name__)

class ProtocolRegistry:
    """Registry for managing multiple swap protocols."""

    def __init__(self):
        """Initialize available protocols."""
        self.protocols: Dict[str, Any] = {}
        self._initialize_protocols()

    async def close(self):
        """Close all protocol clients."""
        for protocol in self.protocols.values():
            if hasattr(protocol, 'close'):
                await protocol.close()

    def _initialize_protocols(self):
        """Initialize supported protocols."""
        try:
            self.protocols["0x"] = ZeroXAdapter()
            logger.info("Initialized 0x protocol adapter")
        except Exception as e:
            logger.error(f"Failed to initialize 0x protocol adapter: {e}")

        try:
            self.protocols["brian"] = BrianAdapter()
            logger.info("Initialized Brian protocol adapter")
        except Exception as e:
            logger.error(f"Failed to initialize Brian protocol adapter: {e}")

    def get_protocol(self, protocol_id: str) -> Optional[Any]:
        """Get a specific protocol by ID."""
        return self.protocols.get(protocol_id)

    def get_supported_protocols(self, chain_id: int) -> List[Any]:
        """Get list of protocols that support the given chain."""
        return [
            protocol for protocol in self.protocols.values()
            if protocol.is_supported(chain_id)
        ]

    def get_preferred_protocol(self, chain_id: int) -> Optional[Any]:
        """Get the preferred protocol for a given chain."""
        # Prefer Brian if available
        brian = self.get_protocol("brian")
        if brian and brian.is_supported(chain_id):
            return brian

        # Fall back to 0x for other chains
        zerox = self.get_protocol("0x")
        if zerox and zerox.is_supported(chain_id):
            return zerox

        # No supported protocols
        return None

    async def resolve_token(self, chain_id: int, token_identifier: str) -> Optional[TokenInfo]:
        """
        Resolve token identifier to token info with fallback to token service.

        Args:
            chain_id: Chain ID
            token_identifier: Token identifier (symbol, address, etc.)

        Returns:
            TokenInfo if found, None otherwise
        """
        # First try manual registry for common tokens (fast path)
        token = token_registry.get_token(token_identifier)
        if token and token.is_supported_on_chain(chain_id):
            return token

        # If it looks like an address, try by address in registry
        if token_identifier.startswith("0x") and len(token_identifier) >= 40:
            token = token_registry.get_token_by_address(chain_id, token_identifier)
            if token:
                return token

        # Fallback to scalable token service
        try:
            token_info = await token_service.get_token_info(chain_id, token_identifier)
            if token_info:
                # Convert token service response to TokenInfo for compatibility
                return TokenInfo(
                    id=token_identifier.lower(),
                    name=token_info.get("name", token_identifier.upper()),
                    symbol=token_info.get("symbol", token_identifier.upper()),
                    decimals=token_info.get("metadata", {}).get("decimals", 18),
                    type="erc20" if token_info.get("address") else "native",
                    verified=token_info.get("metadata", {}).get("verified", False),
                    addresses={chain_id: token_info.get("address", "")} if token_info.get("address") else {}
                )
        except Exception as e:
            logger.warning(f"Token service lookup failed for {token_identifier}: {e}")

        # Not found
        return None


# Global instance
protocol_registry = ProtocolRegistry()