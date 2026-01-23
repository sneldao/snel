"""
Token models and registry for cross-chain token handling.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TokenType(str, Enum):
    NATIVE = "native"  # Chain's native token (ETH, MATIC, etc.)
    ERC20 = "erc20"  # Standard ERC20 token
    WRAPPED = "wrapped"  # Wrapped native token (WETH, WMATIC, etc.)
    BRIDGED = "bridged"  # Token bridged from another chain


class TokenInfo(BaseModel):
    """Standardized token information model."""

    id: str  # Canonical token identifier (e.g., "eth", "usdc")
    name: str
    symbol: str
    decimals: int
    type: TokenType
    logo_uri: str | None = Field(default=None)
    verified: bool = False

    # Chain-specific addresses
    addresses: dict[int, str] = Field(default_factory=dict)

    # Optional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_address(self, chain_id: int) -> str | None:
        """Get token address for specific chain."""
        # Native token representation (using ETH address as placeholder for most EVM chains)
        if self.type == TokenType.NATIVE:
            return self.addresses.get(
                chain_id, "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            )
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
        self.tokens: dict[str, TokenInfo] = {}
        self._initialize_common_tokens()

    def _initialize_common_tokens(self):
        """Initialize registry with common tokens."""
        # Native ETH
        self.register_token(
            TokenInfo(
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
                },
            )
        )

        # Native CRO (Cronos)
        self.register_token(
            TokenInfo(
                id="cro",
                name="Cronos",
                symbol="CRO",
                decimals=18,
                type=TokenType.NATIVE,
                verified=True,
                addresses={
                    25: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                    338: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                },
            )
        )

        # WETH on different chains
        self.register_token(
            TokenInfo(
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
                },
            )
        )

        # USDC on different chains
        self.register_token(
            TokenInfo(
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
                    # Cronos USDC (official)
                    25: "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
                    # Cronos Testnet USDC
                    338: "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
                },
                metadata={
                    "mm_finance_addresses": {
                        # MM Finance uses the same official addresses
                        25: "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
                        338: "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
                    },
                    "legacy_addresses": {
                        # Legacy USDC.e addresses for reference
                        25: "0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C",
                        338: "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",
                    }
                }
            )
        )

        # WCRO (Wrapped CRO) for Cronos
        self.register_token(
            TokenInfo(
                id="wcro",
                name="Wrapped CRO",
                symbol="WCRO",
                decimals=18,
                type=TokenType.WRAPPED,
                verified=True,
                addresses={
                    # Standard WCRO (official Cronos addresses)
                    25: "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
                    338: "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
                },
                metadata={
                    "mm_finance_addresses": {
                        # MM Finance uses the same official addresses
                        25: "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
                        338: "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
                    }
                }
            )
        )

        # USDT on different chains
        self.register_token(
            TokenInfo(
                id="usdt",
                name="Tether USD",
                symbol="USDT",
                decimals=6,
                type=TokenType.ERC20,
                verified=True,
                addresses={
                    # Ethereum USDT
                    1: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                    # Arbitrum USDT
                    42161: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
                    # Polygon USDT
                    137: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
                    # BSC USDT
                    56: "0x55d398326f99059fF775485246999027B3197955",
                    # Avalanche USDT
                    43114: "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
                    # Cronos USDT
                    25: "0x66e428c3f67a68878562e79A0234c1F83c208770",
                    # Cronos Testnet USDT
                    338: "0x87EFB3ec1576Dec8ED47e58B832bEdCd86eE186e",
                },
            )
        )

        # MNEE - Multi-chain USD-backed stablecoin
        self.register_token(
            TokenInfo(
                id="mnee",
                name="MNEE Stablecoin",
                symbol="MNEE",
                decimals=18,  # 18 decimals on Ethereum (standard ERC20), not 5
                type=TokenType.ERC20,  # ERC20 on Ethereum, native protocol on 1Sat Ordinals
                verified=True,
                addresses={
                    # 1Sat Ordinals (primary network)
                    236: "1SAT_ORDINALS",
                    # Ethereum (multi-chain support)
                    1: "0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF",
                },
                metadata={
                    "primary_network": "1Sat Ordinals",
                    "protocol": "1Sat Ordinals / ERC-20",
                    "description": "Fast, USD-backed stablecoin on 1Sat Ordinals protocol",
                    "features": [
                        "instant_transactions",
                        "gasless_ux",
                        "near_zero_fees",
                        "multi_chain",
                    ],
                    "collateral": "1:1 USD backed by U.S. Treasury bills and cash equivalents",
                    "regulation": "Regulated in Antigua with full AML/KYC compliance",
                    "sdk": "@mnee/ts-sdk",
                    "github": "https://github.com/mnee-xyz/mnee",
                },
            )
        )

    def register_token(self, token: TokenInfo):
        """Register a token in the registry."""
        self.tokens[token.id] = token

    def get_token(self, identifier: str) -> TokenInfo | None:
        """Get token by canonical ID or symbol."""
        # Direct lookup by ID
        if identifier in self.tokens:
            return self.tokens[identifier]

        # Case-insensitive lookup by ID or symbol
        identifier_lower = identifier.lower()
        for token in self.tokens.values():
            if (
                token.id.lower() == identifier_lower
                or token.symbol.lower() == identifier_lower
            ):
                return token

        return None

    def get_token_by_address(self, chain_id: int, address: str) -> TokenInfo | None:
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

    def get_supported_tokens(self, chain_id: int) -> list[TokenInfo]:
        """Get all tokens supported on a specific chain."""
        return [
            token
            for token in self.tokens.values()
            if token.is_supported_on_chain(chain_id)
        ]


# Global instance
token_registry = TokenRegistry()
