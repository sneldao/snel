"""
Agent configuration and capability definitions for SNEL.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class AgentMode(Enum):
    """Different modes the agent can operate in."""
    CONVERSATIONAL = "conversational"  # Full chat experience
    DIRECT = "direct"  # Direct, action-focused responses
    TECHNICAL = "technical"  # Detailed technical information

@dataclass
class AgentCapability:
    """Represents a specific capability of the agent."""
    name: str
    description: str
    supported_chains: List[int]
    required_protocols: List[str]
    examples: List[str]

class AgentConfig:
    """Configuration for the SNEL agent behavior and capabilities."""
    
    # Core capabilities
    CAPABILITIES = {
        "token_swaps": AgentCapability(
            name="Token Swaps",
            description="Execute token swaps across multiple chains using DEX aggregators",
            supported_chains=[1, 8453, 42161, 10, 137, 43114, 56, 534352, 324, 59144, 5000, 81457, 100, 8217],
            required_protocols=["0x", "brian"],
            examples=[
                "swap 1 ETH for USDC",
                "swap $100 worth of USDC for WBTC",
                "exchange 0.5 BNB for CAKE on BSC"
            ]
        ),
        "cross_chain_bridging": AgentCapability(
            name="Cross-Chain Bridging",
            description="Bridge assets between different blockchain networks",
            supported_chains=[1, 8453, 42161, 10, 137, 43114, 56, 534352],
            required_protocols=["brian"],
            examples=[
                "bridge 0.1 ETH from Ethereum to Base",
                "move 100 USDC from Polygon to Arbitrum",
                "bridge ETH from Base to Scroll"
            ]
        ),
        "portfolio_management": AgentCapability(
            name="Portfolio Management",
            description="Check balances and monitor transactions across chains",
            supported_chains=[1, 8453, 42161, 10, 137, 43114, 56, 534352, 324, 59144, 5000, 81457, 100, 8217],
            required_protocols=["rpc"],
            examples=[
                "show my ETH balance",
                "check my portfolio on Base",
                "what's my USDC balance across all chains"
            ]
        ),
        "price_information": AgentCapability(
            name="Price Information",
            description="Get real-time token prices and market data",
            supported_chains=[1, 8453, 42161, 10, 137, 43114, 56, 534352, 324, 59144, 5000, 81457, 100, 8217],
            required_protocols=["coingecko", "0x"],
            examples=[
                "what's the price of ETH",
                "show me USDC/ETH rate",
                "get current gas prices on Ethereum"
            ]
        )
    }
    
    # Chain information
    SUPPORTED_CHAINS = {
        1: {"name": "Ethereum", "symbol": "ETH", "type": "L1"},
        8453: {"name": "Base", "symbol": "ETH", "type": "L2"},
        42161: {"name": "Arbitrum One", "symbol": "ETH", "type": "L2"},
        10: {"name": "Optimism", "symbol": "ETH", "type": "L2"},
        137: {"name": "Polygon", "symbol": "MATIC", "type": "L1"},
        43114: {"name": "Avalanche", "symbol": "AVAX", "type": "L1"},
        56: {"name": "BNB Chain", "symbol": "BNB", "type": "L1"},
        534352: {"name": "Scroll", "symbol": "ETH", "type": "L2"},
        324: {"name": "zkSync Era", "symbol": "ETH", "type": "L2"},
        59144: {"name": "Linea", "symbol": "ETH", "type": "L2"},
        5000: {"name": "Mantle", "symbol": "MNT", "type": "L2"},
        81457: {"name": "Blast", "symbol": "ETH", "type": "L2"},
        100: {"name": "Gnosis", "symbol": "xDAI", "type": "L1"},
        34443: {"name": "Mode", "symbol": "ETH", "type": "L2"},
        167000: {"name": "Taiko", "symbol": "ETH", "type": "L2"},
        1101: {"name": "Starknet", "symbol": "ETH", "type": "L2"},
        8217: {"name": "Kaia", "symbol": "KAIA", "type": "L1"}
    }
    
    # Protocol capabilities
    PROTOCOL_CAPABILITIES = {
        "0x": {
            "name": "0x Protocol",
            "description": "Professional DEX aggregator with deep liquidity",
            "supported_chains": [1, 8453, 42161, 10, 137, 43114, 56, 81457],
            "features": ["swap", "limit_orders", "rfq"]
        },
        "brian": {
            "name": "Brian API",
            "description": "AI-powered DeFi protocol aggregator",
            "supported_chains": [1, 8453, 42161, 10, 137, 43114, 56, 534352, 324, 59144, 5000, 100, 1101],
            "features": ["swap", "bridge", "natural_language"]
        }
    }
    
    # Response templates
    RESPONSE_TEMPLATES = {
        "swap_confirmation": "I'll help you swap {amount} {from_token} for {to_token} on {chain}. Let me get quotes from available protocols.",
        "unsupported_chain": "I don't support operations on {chain} yet. Supported chains: {supported_chains}",
        "missing_info": "I need more information: {missing_fields}",
        "error_generic": "I encountered an issue: {error}. Please try again or contact support.",
        "success_swap": "✅ Swap successful! {amount} {from_token} → {to_token} on {chain}. Transaction: {tx_hash}"
    }
    
    @classmethod
    def get_capabilities_for_chain(cls, chain_id: int) -> List[AgentCapability]:
        """Get available capabilities for a specific chain."""
        return [
            capability for capability in cls.CAPABILITIES.values()
            if chain_id in capability.supported_chains
        ]
    
    @classmethod
    def get_chain_name(cls, chain_id: int) -> str:
        """Get human-readable chain name."""
        return cls.SUPPORTED_CHAINS.get(chain_id, {}).get("name", f"Chain {chain_id}")
    
    @classmethod
    def is_chain_supported(cls, chain_id: int) -> bool:
        """Check if a chain is supported."""
        return chain_id in cls.SUPPORTED_CHAINS
    
    @classmethod
    def get_supported_protocols_for_chain(cls, chain_id: int) -> List[str]:
        """Get protocols that support a specific chain."""
        return [
            protocol_id for protocol_id, protocol_info in cls.PROTOCOL_CAPABILITIES.items()
            if chain_id in protocol_info["supported_chains"]
        ]
