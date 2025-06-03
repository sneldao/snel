"""
Shared chain utilities for DRY principle.
Centralized chain information and mapping functions.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class ChainInfo:
    """Information about a blockchain network."""
    id: int
    name: str
    display_name: str
    native_token: str
    rpc_url: Optional[str] = None
    explorer_url: Optional[str] = None
    is_testnet: bool = False


class ChainRegistry:
    """Centralized registry for blockchain network information."""
    
    # Comprehensive chain mapping
    CHAINS: Dict[int, ChainInfo] = {
        1: ChainInfo(
            id=1,
            name="ethereum",
            display_name="Ethereum",
            native_token="ETH",
            rpc_url="https://eth.llamarpc.com",
            explorer_url="https://etherscan.io"
        ),
        10: ChainInfo(
            id=10,
            name="optimism",
            display_name="Optimism",
            native_token="ETH",
            rpc_url="https://mainnet.optimism.io",
            explorer_url="https://optimistic.etherscan.io"
        ),
        56: ChainInfo(
            id=56,
            name="bsc",
            display_name="BSC",
            native_token="BNB",
            rpc_url="https://bsc-dataseed.binance.org",
            explorer_url="https://bscscan.com"
        ),
        137: ChainInfo(
            id=137,
            name="polygon",
            display_name="Polygon",
            native_token="MATIC",
            rpc_url="https://polygon-rpc.com",
            explorer_url="https://polygonscan.com"
        ),
        324: ChainInfo(
            id=324,
            name="zksync",
            display_name="ZK Sync",
            native_token="ETH",
            rpc_url="https://mainnet.era.zksync.io",
            explorer_url="https://explorer.zksync.io"
        ),
        8453: ChainInfo(
            id=8453,
            name="base",
            display_name="Base",
            native_token="ETH",
            rpc_url="https://mainnet.base.org",
            explorer_url="https://basescan.org"
        ),
        42161: ChainInfo(
            id=42161,
            name="arbitrum",
            display_name="Arbitrum",
            native_token="ETH",
            rpc_url="https://arb1.arbitrum.io/rpc",
            explorer_url="https://arbiscan.io"
        ),
        43114: ChainInfo(
            id=43114,
            name="avalanche",
            display_name="Avalanche",
            native_token="AVAX",
            rpc_url="https://api.avax.network/ext/bc/C/rpc",
            explorer_url="https://snowtrace.io"
        ),
        59144: ChainInfo(
            id=59144,
            name="linea",
            display_name="Linea",
            native_token="ETH",
            rpc_url="https://rpc.linea.build",
            explorer_url="https://lineascan.build"
        ),
        534352: ChainInfo(
            id=534352,
            name="scroll",
            display_name="Scroll",
            native_token="ETH",
            rpc_url="https://rpc.scroll.io",
            explorer_url="https://scrollscan.com"
        ),
        5000: ChainInfo(
            id=5000,
            name="mantle",
            display_name="Mantle",
            native_token="MNT",
            rpc_url="https://rpc.mantle.xyz",
            explorer_url="https://explorer.mantle.xyz"
        ),
        81457: ChainInfo(
            id=81457,
            name="blast",
            display_name="Blast",
            native_token="ETH",
            rpc_url="https://rpc.blast.io",
            explorer_url="https://blastscan.io"
        )
    }
    
    # Chain name aliases for flexible lookup
    NAME_ALIASES: Dict[str, int] = {
        # Primary names
        "ethereum": 1,
        "eth": 1,
        "optimism": 10,
        "op": 10,
        "bsc": 56,
        "binance": 56,
        "polygon": 137,
        "matic": 137,
        "zksync": 324,
        "zk": 324,
        "base": 8453,
        "arbitrum": 42161,
        "arb": 42161,
        "avalanche": 43114,
        "avax": 43114,
        "linea": 59144,
        "scroll": 534352,
        "mantle": 5000,
        "blast": 81457,
        
        # Alternative names
        "ethereum mainnet": 1,
        "optimism mainnet": 10,
        "binance smart chain": 56,
        "polygon mainnet": 137,
        "zksync era": 324,
        "arbitrum one": 42161,
        "avalanche c-chain": 43114,
    }
    
    @classmethod
    def get_chain_info(cls, chain_id: int) -> Optional[ChainInfo]:
        """Get chain information by ID."""
        return cls.CHAINS.get(chain_id)
    
    @classmethod
    def get_chain_name(cls, chain_id: int) -> str:
        """Get chain display name by ID."""
        chain_info = cls.get_chain_info(chain_id)
        return chain_info.display_name if chain_info else f"Chain {chain_id}"
    
    @classmethod
    def get_chain_id_by_name(cls, name: str) -> Optional[int]:
        """Get chain ID by name (case-insensitive)."""
        return cls.NAME_ALIASES.get(name.lower().strip())
    
    @classmethod
    def get_native_token(cls, chain_id: int) -> str:
        """Get native token symbol for a chain."""
        chain_info = cls.get_chain_info(chain_id)
        return chain_info.native_token if chain_info else "ETH"
    
    @classmethod
    def is_supported(cls, chain_id: int) -> bool:
        """Check if a chain is supported."""
        return chain_id in cls.CHAINS
    
    @classmethod
    def get_supported_chains(cls) -> List[ChainInfo]:
        """Get list of all supported chains."""
        return list(cls.CHAINS.values())
    
    @classmethod
    def get_supported_chain_ids(cls) -> List[int]:
        """Get list of all supported chain IDs."""
        return list(cls.CHAINS.keys())
    
    @classmethod
    def get_explorer_url(cls, chain_id: int, tx_hash: Optional[str] = None) -> Optional[str]:
        """Get explorer URL for a chain, optionally with transaction hash."""
        chain_info = cls.get_chain_info(chain_id)
        if not chain_info or not chain_info.explorer_url:
            return None
        
        if tx_hash:
            return f"{chain_info.explorer_url}/tx/{tx_hash}"
        
        return chain_info.explorer_url
    
    @classmethod
    def format_chain_list(cls, chain_ids: List[int]) -> str:
        """Format a list of chain IDs as human-readable names."""
        names = [cls.get_chain_name(chain_id) for chain_id in chain_ids]
        
        if len(names) == 0:
            return "no chains"
        elif len(names) == 1:
            return names[0]
        elif len(names) == 2:
            return f"{names[0]} and {names[1]}"
        else:
            return f"{', '.join(names[:-1])}, and {names[-1]}"


# Convenience functions for backward compatibility
def get_chain_name(chain_id: int) -> str:
    """Get chain name - backward compatibility wrapper."""
    return ChainRegistry.get_chain_name(chain_id)


def get_chain_id_by_name(name: str) -> Optional[int]:
    """Get chain ID by name - backward compatibility wrapper."""
    return ChainRegistry.get_chain_id_by_name(name)


def is_chain_supported(chain_id: int) -> bool:
    """Check if chain is supported - backward compatibility wrapper."""
    return ChainRegistry.is_supported(chain_id)
