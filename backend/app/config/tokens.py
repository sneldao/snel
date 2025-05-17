"""
Common token addresses and configurations across chains.
"""
from typing import Dict, Any

# Common token addresses by chain
COMMON_TOKENS: Dict[int, Dict[str, Dict[str, Any]]] = {
    1: {  # Ethereum Mainnet
        "eth": {
            "address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            "name": "Ethereum",
            "symbol": "ETH",
            "decimals": 18,
            "verified": True
        },
        "usdc": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "verified": True
        },
        "weth": {
            "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "name": "Wrapped Ether",
            "symbol": "WETH",
            "decimals": 18,
            "verified": True
        }
    },
    42161: {  # Arbitrum One
        "eth": {
            "address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            "name": "Ethereum",
            "symbol": "ETH",
            "decimals": 18,
            "verified": True
        },
        "usdc": {
            "address": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "verified": True
        },
        "weth": {
            "address": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "name": "Wrapped Ether",
            "symbol": "WETH",
            "decimals": 18,
            "verified": True
        }
    },
    137: {  # Polygon
        "eth": {
            "address": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
            "name": "Ethereum",
            "symbol": "ETH",
            "decimals": 18,
            "verified": True
        },
        "usdc": {
            "address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "verified": True
        },
        "weth": {
            "address": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
            "name": "Wrapped Ether",
            "symbol": "WETH",
            "decimals": 18,
            "verified": True
        }
    }
}

def get_token_info(chain_id: int, symbol: str) -> Dict[str, Any]:
    """Get token information for a given chain and symbol."""
    chain_tokens = COMMON_TOKENS.get(chain_id, {})
    token_info = chain_tokens.get(symbol.lower(), None)
    
    if token_info:
        return {
            "address": token_info["address"],
            "symbol": token_info["symbol"],
            "name": token_info["name"],
            "metadata": {
                "verified": token_info["verified"],
                "source": "registry",
                "decimals": token_info["decimals"]
            }
        }
    return None

def get_chain_name(chain_id: int) -> str:
    """Get the name of a chain from its ID."""
    chain_names = {
        1: "Ethereum",
        42161: "Arbitrum One",
        137: "Polygon",
        10: "Optimism",
        56: "BNB Chain",
        43114: "Avalanche",
        8453: "Base",
        534352: "Scroll",
    }
    return chain_names.get(chain_id, f"Chain {chain_id}") 