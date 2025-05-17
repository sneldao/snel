"""
Chain configuration and support definitions.
"""
from enum import Enum
from typing import Dict, Set, List, Optional
from dataclasses import dataclass

class ChainType(Enum):
    """Types of blockchain networks."""
    EVM = "evm"
    STARKNET = "starknet"
    SOLANA = "solana"

@dataclass
class ChainInfo:
    """Information about a blockchain network."""
    id: int  # Chain ID
    name: str  # Human readable name
    type: ChainType  # Chain type (EVM, Starknet, etc.)
    rpc_url: Optional[str] = None  # Default RPC URL if any
    explorer_url: Optional[str] = None  # Block explorer URL
    supported_protocols: Set[str] = None  # Set of supported protocols (0x, Brian, etc.)

    def __post_init__(self):
        if self.supported_protocols is None:
            self.supported_protocols = set()

# Define supported chains with their capabilities
CHAINS: Dict[int, ChainInfo] = {
    # Layer 1
    1: ChainInfo(
        id=1,
        name="Ethereum",
        type=ChainType.EVM,
        explorer_url="https://etherscan.io/tx/",
        supported_protocols={"0x", "brian"}
    ),
    56: ChainInfo(
        id=56,
        name="BNB Chain",
        type=ChainType.EVM,
        explorer_url="https://bscscan.com/tx/",
        supported_protocols={"0x", "brian"}
    ),
    100: ChainInfo(
        id=100,
        name="Gnosis",
        type=ChainType.EVM,
        explorer_url="https://gnosisscan.io/tx/",
        supported_protocols={"brian"}
    ),
    
    # Layer 2 & Rollups
    8453: ChainInfo(
        id=8453,
        name="Base",
        type=ChainType.EVM,
        explorer_url="https://basescan.org/tx/",
        supported_protocols={"0x", "brian"}
    ),
    10: ChainInfo(
        id=10,
        name="Optimism",
        type=ChainType.EVM,
        explorer_url="https://optimistic.etherscan.io/tx/",
        supported_protocols={"0x", "brian"}
    ),
    42161: ChainInfo(
        id=42161,
        name="Arbitrum",
        type=ChainType.EVM,
        explorer_url="https://arbiscan.io/tx/",
        supported_protocols={"0x", "brian"}
    ),
    137: ChainInfo(
        id=137,
        name="Polygon",
        type=ChainType.EVM,
        explorer_url="https://polygonscan.com/tx/",
        supported_protocols={"0x", "brian"}
    ),
    59144: ChainInfo(
        id=59144,
        name="Linea",
        type=ChainType.EVM,
        explorer_url="https://lineascan.build/tx/",
        supported_protocols={"0x", "brian"}
    ),
    534352: ChainInfo(
        id=534352,
        name="Scroll",
        type=ChainType.EVM,
        explorer_url="https://scrollscan.com/tx/",
        supported_protocols={"0x", "brian"}
    ),
    324: ChainInfo(
        id=324,
        name="zkSync Era",
        type=ChainType.EVM,
        explorer_url="https://explorer.zksync.io/tx/",
        supported_protocols={"brian"}
    ),
    34443: ChainInfo(
        id=34443,
        name="Mode",
        type=ChainType.EVM,
        explorer_url="https://explorer.mode.network/tx/",
        supported_protocols={"0x", "brian"}
    ),
    167004: ChainInfo(
        id=167004,
        name="Taiko",
        type=ChainType.EVM,
        explorer_url="https://explorer.test.taiko.xyz/tx/",
        supported_protocols={"brian"}
    ),
    
    # Other Networks
    43114: ChainInfo(
        id=43114,
        name="Avalanche",
        type=ChainType.EVM,
        explorer_url="https://snowtrace.io/tx/",
        supported_protocols={"0x"}
    ),
    5000: ChainInfo(
        id=5000,
        name="Mantle",
        type=ChainType.EVM,
        explorer_url="https://explorer.mantle.xyz/tx/",
        supported_protocols={"0x"}
    ),
    81457: ChainInfo(
        id=81457,
        name="Blast",
        type=ChainType.EVM,
        explorer_url="https://blastscan.io/tx/",
        supported_protocols={"0x"}
    ),
    # Starknet
    1101: ChainInfo(
        id=1101,
        name="Starknet",
        type=ChainType.STARKNET,
        explorer_url="https://starkscan.co/tx/",
        supported_protocols={"brian"}
    ),
}

def get_chains_by_type(chain_type: ChainType) -> List[ChainInfo]:
    """Get all chains of a specific type."""
    return [chain for chain in CHAINS.values() if chain.type == chain_type]

def get_chains_by_protocol(protocol: str) -> List[ChainInfo]:
    """Get all chains that support a specific protocol."""
    return [chain for chain in CHAINS.values() if protocol in chain.supported_protocols]

def is_protocol_supported(chain_id: int, protocol: str) -> bool:
    """Check if a specific protocol is supported on a chain."""
    chain = CHAINS.get(chain_id)
    return chain is not None and protocol in chain.supported_protocols

def get_chain_info(chain_id: int) -> Optional[ChainInfo]:
    """Get information about a specific chain."""
    return CHAINS.get(chain_id) 