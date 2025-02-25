from eth_typing import HexAddress
from typing import Dict

class ChainConfig:
    """Configuration for supported chains."""
    SUPPORTED_CHAINS = {
        1: "Ethereum",
        8453: "Base",
        42161: "Arbitrum",
        10: "Optimism",
        137: "Polygon",
        43114: "Avalanche",
        534352: "Scroll"
    }

    @staticmethod
    def is_supported(chain_id: int) -> bool:
        return chain_id in ChainConfig.SUPPORTED_CHAINS

    @staticmethod
    def get_chain_name(chain_id: int) -> str:
        return ChainConfig.SUPPORTED_CHAINS.get(chain_id, "Unknown")

TOKEN_ADDRESSES: Dict[int, Dict[str, HexAddress]] = {
    1: {  # Ethereum
        "ETH": HexAddress("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"),
        "USDC": HexAddress("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),
        "UNI": HexAddress("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"),
    },
    8453: {  # Base
        "ETH": HexAddress("0x4200000000000000000000000000000000000006"),
        "USDC": HexAddress("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        "UNI": HexAddress("0x0000000000000000000000000000000000000000"),
    },
    10: {  # Optimism
        "ETH": HexAddress("0x4200000000000000000000000000000000000006"),
        "USDC": HexAddress("0x7F5c764cBc14f9669B88837ca1490cCa17c31607"),
        "UNI": HexAddress("0x6fd9d7AD17242c41f7131d257212c54A0e816691"),
    },
    42161: {  # Arbitrum
        "ETH": HexAddress("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
        "USDC": HexAddress("0xaf88d065e77c8cC2239327C5EDb3A432268e5831"),
        "UNI": HexAddress("0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0"),
    },
    137: {  # Polygon
        "ETH": HexAddress("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"),
        "USDC": HexAddress("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
        "UNI": HexAddress("0xb33EaAd8d922B1083446DC23f610c2567fB5180f"),
    },
    43114: {  # Avalanche
        "ETH": HexAddress("0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB"),
        "USDC": HexAddress("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"),
        "UNI": HexAddress("0x8eBAf22B6F053dFFeaf46f4Dd9eFA95D89ba8580"),
    },
    534352: {  # Scroll
        "ETH": HexAddress("0x5300000000000000000000000000000000000004"),
        "USDC": HexAddress("0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4"),
        "UNI": HexAddress("0x0000000000000000000000000000000000000000"),
        "SCR": HexAddress("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),  # Scroll token
        "NURI": HexAddress("0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc"),  # NURI token
    }
}

NATIVE_TOKENS = {
    "0x4200000000000000000000000000000000000006",  # WETH on OP/Base
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
    "0x5300000000000000000000000000000000000004",  # ETH on Scroll
} 