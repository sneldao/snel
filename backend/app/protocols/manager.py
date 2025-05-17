"""
Protocol manager for handling multiple swap protocols.
"""
from typing import Dict, List, Optional
from .base import SwapProtocol
from .zerox import ZeroXProtocol
from .brian import BrianProtocol
from ..config.chains import get_chain_info, ChainType

class ProtocolManager:
    """Manager for handling multiple swap protocols."""

    def __init__(self):
        """Initialize available protocols."""
        self.protocols: Dict[str, SwapProtocol] = {}
        self._initialize_protocols()

    def _initialize_protocols(self):
        """Initialize supported protocols."""
        try:
            self.protocols["0x"] = ZeroXProtocol()
        except ValueError as e:
            print(f"Failed to initialize 0x protocol: {e}")

        try:
            self.protocols["brian"] = BrianProtocol()
        except ValueError as e:
            print(f"Failed to initialize Brian protocol: {e}")

    def get_supported_protocols(self, chain_id: int) -> List[SwapProtocol]:
        """Get list of protocols that support the given chain."""
        chain_info = get_chain_info(chain_id)
        if not chain_info:
            return []

        return [
            protocol for protocol in self.protocols.values()
            if protocol.is_supported(chain_id)
        ]

    def get_preferred_protocol(self, chain_id: int) -> Optional[SwapProtocol]:
        """Get the preferred protocol for a given chain."""
        chain_info = get_chain_info(chain_id)
        if not chain_info:
            return None

        # For Starknet, always use Brian
        if chain_info.type == ChainType.STARKNET:
            return self.protocols.get("brian")

        # For EVM chains, prefer Brian if available
        supported = self.get_supported_protocols(chain_id)
        if not supported:
            return None

        # Prefer Brian for supported chains
        brian = self.protocols.get("brian")
        if brian and brian.is_supported(chain_id):
            return brian

        # Fall back to 0x for other EVM chains
        return supported[0]

    def get_protocol(self, name: str) -> Optional[SwapProtocol]:
        """Get a specific protocol by name."""
        return self.protocols.get(name) 