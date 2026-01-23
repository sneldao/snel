"""
Chain configuration and support definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChainType(Enum):
    """Types of blockchain networks."""

    EVM = "evm"
    STARKNET = "starknet"
    SOLANA = "solana"


@dataclass
class PrivacyCapabilities:
    """Privacy capabilities for a blockchain network."""

    x402_support: bool = False  # Supports x402 programmatic privacy
    gmp_privacy: bool = False  # Supports GMP-based privacy bridging
    compliance_support: bool = False  # Supports compliance-ready privacy
    direct_zcash: bool = False  # Supports direct Zcash transactions


@dataclass
class ChainInfo:
    """Information about a blockchain network."""

    id: int  # Chain ID
    name: str  # Human readable name
    type: ChainType  # Chain type (EVM, Starknet, etc.)
    rpc_url: str | None = None  # Default RPC URL if any
    explorer_url: str | None = None  # Block explorer URL
    supported_protocols: set[str] = field(
        default_factory=set
    )  # Set of supported protocols (0x, Brian, etc.)
    privacy: PrivacyCapabilities = field(
        default_factory=PrivacyCapabilities
    )  # Privacy capabilities


# Define supported chains with their capabilities
CHAINS: dict[int, ChainInfo] = {
    # Layer 1
    1: ChainInfo(
        id=1,
        name="Ethereum",
        type=ChainType.EVM,
        explorer_url="https://etherscan.io/tx/",
        supported_protocols={"0x", "brian", "x402"},  # x402 via MNEE stablecoin
        privacy=PrivacyCapabilities(
            x402_support=True,  # Full x402 privacy support via MNEE
            gmp_privacy=True,  # GMP privacy fallback
            compliance_support=True,  # Compliance-ready privacy
        ),
    ),
    56: ChainInfo(
        id=56,
        name="BNB Chain",
        type=ChainType.EVM,
        explorer_url="https://bscscan.com/tx/",
        supported_protocols={"0x", "brian"},
    ),
    100: ChainInfo(
        id=100,
        name="Gnosis",
        type=ChainType.EVM,
        explorer_url="https://gnosisscan.io/tx/",
        supported_protocols={"brian"},
    ),
    # Layer 2 & Rollups
    8453: ChainInfo(
        id=8453,
        name="Base",
        type=ChainType.EVM,
        explorer_url="https://basescan.org/tx/",
        supported_protocols={"0x", "brian"},
        privacy=PrivacyCapabilities(
            x402_support=True,  # Full x402 privacy support
            gmp_privacy=True,  # GMP privacy fallback
            compliance_support=True,  # Compliance-ready privacy
        ),
    ),
    10: ChainInfo(
        id=10,
        name="Optimism",
        type=ChainType.EVM,
        explorer_url="https://optimistic.etherscan.io/tx/",
        supported_protocols={"0x", "brian"},
    ),
    42161: ChainInfo(
        id=42161,
        name="Arbitrum",
        type=ChainType.EVM,
        explorer_url="https://arbiscan.io/tx/",
        supported_protocols={"0x", "brian"},
    ),
    137: ChainInfo(
        id=137,
        name="Polygon",
        type=ChainType.EVM,
        explorer_url="https://polygonscan.com/tx/",
        supported_protocols={"0x", "brian"},
        privacy=PrivacyCapabilities(
            x402_support=True,  # Full x402 privacy support
            gmp_privacy=True,  # GMP privacy fallback
            compliance_support=True,  # Compliance-ready privacy
        ),
    ),
    59144: ChainInfo(
        id=59144,
        name="Linea",
        type=ChainType.EVM,
        explorer_url="https://lineascan.build/tx/",
        supported_protocols={"0x", "brian"},
    ),
    534352: ChainInfo(
        id=534352,
        name="Scroll",
        type=ChainType.EVM,
        explorer_url="https://scrollscan.com/tx/",
        supported_protocols={"0x", "brian"},
        privacy=PrivacyCapabilities(
            x402_support=False,  # No x402 support (yet)
            gmp_privacy=True,  # GMP privacy fallback only
            compliance_support=False,  # No compliance support
        ),
    ),
    324: ChainInfo(
        id=324,
        name="zkSync Era",
        type=ChainType.EVM,
        explorer_url="https://explorer.zksync.io/tx/",
        supported_protocols={"brian"},
    ),
    34443: ChainInfo(
        id=34443,
        name="Mode",
        type=ChainType.EVM,
        explorer_url="https://explorer.mode.network/tx/",
        supported_protocols={"0x", "brian"},
    ),
    167004: ChainInfo(
        id=167004,
        name="Taiko",
        type=ChainType.EVM,
        explorer_url="https://explorer.test.taiko.xyz/tx/",
        supported_protocols={"brian"},
    ),
    # Privacy Networks
    1337: ChainInfo(
        id=1337,
        name="Zcash",
        type=ChainType.EVM,
        explorer_url="https://zcashblockexplorer.com/tx/",
        supported_protocols=set(),  # No standard protocols, privacy-only
        privacy=PrivacyCapabilities(
            x402_support=False,  # No x402 (direct privacy only)
            gmp_privacy=False,  # No GMP (direct privacy only)
            compliance_support=True,  # Full compliance support
            direct_zcash=True,  # Direct Zcash transactions
        ),
    ),
    # Other Networks
    43114: ChainInfo(
        id=43114,
        name="Avalanche",
        type=ChainType.EVM,
        explorer_url="https://snowtrace.io/tx/",
        supported_protocols={"0x"},
    ),
    5000: ChainInfo(
        id=5000,
        name="Mantle",
        type=ChainType.EVM,
        explorer_url="https://explorer.mantle.xyz/tx/",
        supported_protocols={"0x"},
    ),
    81457: ChainInfo(
        id=81457,
        name="Blast",
        type=ChainType.EVM,
        explorer_url="https://blastscan.io/tx/",
        supported_protocols={"0x"},
    ),
    # Cronos EVM Networks
    25: ChainInfo(
        id=25,
        name="Cronos",
        type=ChainType.EVM,
        rpc_url="https://evm.cronos.org",
        explorer_url="https://cronoscan.com/tx/",
        supported_protocols={"0x", "brian", "x402"},
        privacy=PrivacyCapabilities(
            x402_support=True,  # Full x402 agentic payment support
            gmp_privacy=True,  # GMP privacy fallback
            compliance_support=True,  # Compliance-ready privacy
        ),
    ),
    338: ChainInfo(
        id=338,
        name="Cronos Testnet",
        type=ChainType.EVM,
        rpc_url="https://evm-t3.cronos.org",
        explorer_url="https://testnet.cronoscan.com/tx/",
        supported_protocols={"0x", "brian", "x402"},
        privacy=PrivacyCapabilities(
            x402_support=True,  # Full x402 agentic payment support
            gmp_privacy=True,  # GMP privacy fallback
            compliance_support=True,  # Compliance-ready privacy
        ),
    ),
    # Starknet
    1101: ChainInfo(
        id=1101,
        name="Starknet",
        type=ChainType.STARKNET,
        explorer_url="https://starkscan.co/tx/",
        supported_protocols={"brian"},
    ),
}


def get_chains_by_type(chain_type: ChainType) -> list[ChainInfo]:
    """Get all chains of a specific type."""
    return [chain for chain in CHAINS.values() if chain.type == chain_type]


def get_chains_by_protocol(protocol: str) -> list[ChainInfo]:
    """Get all chains that support a specific protocol."""
    return [chain for chain in CHAINS.values() if protocol in chain.supported_protocols]


def is_protocol_supported(chain_id: int, protocol: str) -> bool:
    """Check if a specific protocol is supported on a chain."""
    chain = CHAINS.get(chain_id)
    return chain is not None and protocol in chain.supported_protocols


def get_chain_info(chain_id: int) -> ChainInfo | None:
    """Get information about a specific chain."""
    return CHAINS.get(chain_id)


def get_chain_id_by_name(chain_name: str) -> int | None:
    """Get chain ID by chain name (case-insensitive)."""
    chain_name_lower = chain_name.lower()
    for chain_id, chain_info in CHAINS.items():
        if chain_info.name.lower() == chain_name_lower:
            return chain_id
    return None


def get_chain_name(chain_id: int) -> str:
    """Get chain name by chain ID."""
    chain = CHAINS.get(chain_id)
    return chain.name if chain else f"Chain {chain_id}"


def get_privacy_capabilities(chain_id: int) -> PrivacyCapabilities:
    """Get privacy capabilities for a specific chain."""
    chain = CHAINS.get(chain_id)
    return chain.privacy if chain else PrivacyCapabilities()


def is_x402_privacy_supported(chain_id: int) -> bool:
    """Check if x402 privacy is supported on a chain."""
    return get_privacy_capabilities(chain_id).x402_support


def is_gmp_privacy_supported(chain_id: int) -> bool:
    """Check if GMP privacy is supported on a chain."""
    return get_privacy_capabilities(chain_id).gmp_privacy


def is_compliance_supported(chain_id: int) -> bool:
    """Check if compliance-ready privacy is supported on a chain."""
    return get_privacy_capabilities(chain_id).compliance_support
