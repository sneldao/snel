"""
Token models and registry for cross-chain token handling.
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel


class TokenType(str, Enum):
    NATIVE = "native"  # Chain's native token (ETH, MATIC, etc.)
    ERC20 = "erc20"    # Standard ERC20 token
    WRAPPED = "wrapped"  # Wrapped native token (WETH, WMATIC, etc.)
    BRIDGED = "bridged"  # Token bridged from another chain


class TokenInfo(BaseModel):
    """Standardized token information model."""
    id: str  # Canonical token identifier (e.g., "eth", "usdc")
    name: str
    symbol: str
    decimals: int
    type: TokenType
    logo_uri: Optional[str] = None
    verified: bool = False

    # Chain-specific addresses
    addresses: Dict[int, str] = {}

    # Optional metadata
    metadata: Dict[str, Any] = {}

    def get_address(self, chain_id: int) -> Optional[str]:
        """Get token address for specific chain."""
        # Native ETH representation
        if self.id == "eth" and self.type == TokenType.NATIVE:
            return "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        return self.addresses.get(chain_id)

    def is_supported_on_chain(self, chain_id: int) -> bool:
        """Check if token is supported on specific chain."""
        # Native ETH is supported on all EVM chains
        if self.id == "eth" and self.type == TokenType.NATIVE:
            return True
        return chain_id in self.addresses


class TokenRegistry:
    """Central registry for token information across chains."""

    def __init__(self):
        """Initialize registry with common tokens."""
        self.tokens: Dict[str, TokenInfo] = {}
        self._initialize_common_tokens()

    def _initialize_common_tokens(self):
        """Initialize registry with common tokens."""
        # Native ETH
        self.register_token(TokenInfo(
            id="eth",
            name="Ethereum",
            symbol="ETH",
            decimals=18,
            type=TokenType.NATIVE,
            verified=True,
            addresses={
                # ETH has the same special address on all EVM chains
                1: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                10: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                56: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                137: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                42161: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                8453: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                43114: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                59144: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                5000: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # Mantle
                81457: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # Blast
            }
        ))

        # WETH on different chains
        self.register_token(TokenInfo(
            id="weth",
            name="Wrapped Ether",
            symbol="WETH",
            decimals=18,
            type=TokenType.WRAPPED,
            verified=True,
            addresses={
                1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                137: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
                10: "0x4200000000000000000000000000000000000006",
                8453: "0x4200000000000000000000000000000000000006",
            }
        ))

        # USDC on different chains
        self.register_token(TokenInfo(
            id="usdc",
            name="USD Coin",
            symbol="USDC",
            decimals=6,
            type=TokenType.ERC20,
            verified=True,
            addresses={
                # Mainnet USDC
                1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                # Arbitrum USDC
                42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                # Polygon USDC
                137: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
                # Optimism USDC
                10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
                # Base USDC
                8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                # BSC USDC
                56: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
                # Avalanche USDC
                43114: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                # Linea USDC
                59144: "0x176211869cA2b568f2A7D4EE941E073a821EE1ff",
                # ZkSync USDC
                324: "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
                # Gnosis USDC
                100: "0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83",
                # Mantle USDC
                5000: "0x09Bc4E0D864854c6aFB6eB9A9cdF58aC190D0dF9",
                # Blast USDC
                81457: "0x4300000000000000000000000000000000000003",
            }
        ))

    def register_token(self, token: TokenInfo):
        """Register a token in the registry."""
        self.tokens[token.id] = token

    def get_token(self, identifier: str) -> Optional[TokenInfo]:
        """Get token by canonical ID or symbol."""
        # Direct lookup by ID
        if identifier in self.tokens:
            return self.tokens[identifier]

        # Case-insensitive lookup by ID or symbol
        identifier_lower = identifier.lower()
        for token in self.tokens.values():
            if token.id.lower() == identifier_lower or token.symbol.lower() == identifier_lower:
                return token

        return None

    def get_token_by_address(self, chain_id: int, address: str) -> Optional[TokenInfo]:
        """Get token by chain and address."""
        address_lower = address.lower()

        # Special handling for ETH address
        if address_lower == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            return self.get_token("eth")

        for token in self.tokens.values():
            token_address = token.addresses.get(chain_id, "").lower()
            if token_address == address_lower:
                return token

        return None

    def get_supported_tokens(self, chain_id: int) -> List[TokenInfo]:
        """Get all tokens supported on a specific chain."""
        return [
            token for token in self.tokens.values()
            if token.is_supported_on_chain(chain_id)
        ]


# Global instance
token_registry = TokenRegistry()