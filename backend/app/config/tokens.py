"""
Common token addresses and configurations across chains.
"""
from typing import Dict, Any

# Common token addresses by chain
COMMON_TOKENS: Dict[int, Dict[str, Dict[str, Any]]] = {
    1: {  # Ethereum Mainnet - MNEE is multi-chain
        "mnee": {
            "address": "0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF",
            "name": "MNEE Stablecoin",
            "symbol": "MNEE",
            "decimals": 5,  # Consistent across chains
            "verified": True,
            "metadata": {
                "protocol": "ERC-20",
                "network": "Ethereum",
                "description": "MNEE on Ethereum - multi-chain USD-backed stablecoin",
                "primary_network": "1Sat Ordinals"
            }
        },
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
    236: {  # 1Sat Ordinals - Chain ID for MNEE's primary network
        "mnee": {
            "address": "1SAT_ORDINALS",  # 1Sat Ordinals protocol
            "name": "MNEE Stablecoin",
            "symbol": "MNEE",
            "decimals": 5,  # 1 MNEE = 100,000 atomic units = 10^5
            "verified": True,
            "metadata": {
                "protocol": "1Sat Ordinals",
                "network": "1Sat Ordinals",
                "description": "Fast, USD-backed stablecoin on 1Sat Ordinals protocol",
                "features": ["instant_transactions", "gasless_ux", "near_zero_fees"],
                "collateral": "1:1 USD backed by U.S. Treasury bills and cash equivalents"
            }
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
    },
    25: {  # Cronos Mainnet
        "cro": {
            "address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # Native token placeholder
            "name": "Cronos",
            "symbol": "CRO",
            "decimals": 18,
            "verified": True
        },
        "wcro": {
            "address": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Wrapped CRO
            "name": "Wrapped Cronos",
            "symbol": "WCRO",
            "decimals": 18,
            "verified": True
        },
        "usdc": {
            "address": "0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C",  # USDC.e on Cronos
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "verified": True
        },
        "usdt": {
            "address": "0x66e428c3f67a68878562e79A0234c1F83c208770",  # USDT on Cronos
            "name": "Tether USD",
            "symbol": "USDT",
            "decimals": 6,
            "verified": True
        },
        "eth": {
            "address": "0xe44Fd7fCb2b1581822D0c862B68222998a0c299a",  # ETH on Cronos
            "name": "Ethereum",
            "symbol": "ETH",
            "decimals": 18,
            "verified": True
        },
        "weth": {
            "address": "0xe44Fd7fCb2b1581822D0c862B68222998a0c299a",  # WETH on Cronos
            "name": "Wrapped Ethereum",
            "symbol": "WETH",
            "decimals": 18,
            "verified": True
        }
    },
    338: {  # Cronos Testnet
        "cro": {
            "address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # Native token placeholder
            "name": "Cronos",
            "symbol": "CRO",
            "decimals": 18,
            "verified": True
        },
        "wcro": {
            "address": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Wrapped CRO (testnet)
            "name": "Wrapped Cronos",
            "symbol": "WCRO",
            "decimals": 18,
            "verified": True
        },
        "usdc": {
            "address": "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",  # devUSDC.e on testnet
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
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
        25: "Cronos",
        338: "Cronos Testnet",
        236: "1Sat Ordinals",  # 1Sat Ordinals network for MNEE
    }
    return chain_names.get(chain_id, f"Chain {chain_id}") 
