"""
Token service for fetching and caching token information from multiple sources.
"""
from typing import Dict, Any, Optional, List
import aiohttp
import json
from redis import Redis
from datetime import timedelta
import os
from web3 import Web3, AsyncWeb3
from web3.exceptions import ContractLogicError
import asyncio

# Standard ERC20 ABI for token info
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class TokenService:
    def __init__(self):
        """Initialize the token service with Redis cache if available."""
        self.use_redis = False
        self.cache = None
        redis_url = os.getenv("REDIS_URL")
        
        # In-memory cache fallback
        self.memory_cache = {}
        
        # Try to connect to Redis if URL is provided
        if redis_url:
            try:
                self.cache = Redis.from_url(redis_url)
                # Test connection
                self.cache.ping()
                self.use_redis = True
                print("Connected to Redis successfully")
            except Exception as e:
                print(f"Redis connection failed: {e}. Using in-memory cache instead.")
                self.use_redis = False
        
        # Initialize Web3 providers for each chain
        self.web3_providers: Dict[int, AsyncWeb3] = {}
        self._setup_web3_providers()
        
        # Default token lists by chain
        self.token_lists = {
            1: [  # Ethereum
                "https://tokens.coingecko.com/uniswap/all.json",
                "https://gateway.ipfs.io/ipns/tokens.uniswap.org",
            ],
            42161: [  # Arbitrum
                "https://tokens.coingecko.com/arbitrum-one/all.json",
                "https://raw.githubusercontent.com/sushiswap/list/master/lists/token-lists/default-token-list/tokens/arbitrum.json",
            ],
            137: [  # Polygon
                "https://tokens.coingecko.com/polygon-pos/all.json",
                "https://raw.githubusercontent.com/sushiswap/list/master/lists/token-lists/default-token-list/tokens/polygon.json",
            ],
        }

    def _setup_web3_providers(self):
        """Set up Web3 providers for each supported chain."""
        # Get RPC URLs from environment variables or use defaults
        rpc_urls = {
            1: os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com"),
            42161: os.getenv("ARB_RPC_URL", "https://arb1.arbitrum.io/rpc"),
            137: os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
            10: os.getenv("OP_RPC_URL", "https://mainnet.optimism.io"),
            56: os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org"),
            8453: os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
            324: os.getenv("ZKSYNC_RPC_URL", "https://mainnet.era.zksync.io"),
            59144: os.getenv("LINEA_RPC_URL", "https://rpc.linea.build"),
            534352: os.getenv("SCROLL_RPC_URL", "https://rpc.scroll.io"),
        }

        # Initialize providers
        for chain_id, rpc_url in rpc_urls.items():
            try:
                self.web3_providers[chain_id] = AsyncWeb3(
                    AsyncWeb3.AsyncHTTPProvider(rpc_url)
                )
            except Exception as e:
                print(f"Failed to initialize Web3 provider for chain {chain_id}: {e}")

    async def get_token_info(self, chain_id: int, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get token information by chain ID and identifier (address or symbol).
        Tries multiple sources in order:
        1. Redis or memory cache
        2. Common tokens (ETH, WETH, etc.)
        3. Token lists
        4. On-chain data
        """
        identifier = identifier.lower()
        
        # Try cache first
        if self.use_redis and self.cache:
            try:
                cached = self.cache.get(f"token:{chain_id}:{identifier}")
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Redis get error: {e}")
        elif f"token:{chain_id}:{identifier}" in self.memory_cache:
            return self.memory_cache[f"token:{chain_id}:{identifier}"]

        # Check if it's a common token
        if identifier in ["eth", "weth", "usdc", "usdt", "dai"]:
            token_info = await self._get_native_token_info(chain_id, identifier)
            if token_info:
                await self._cache_token_info(chain_id, identifier, token_info)
                return token_info

        # Try token lists
        token_info = await self._get_token_from_lists(chain_id, identifier)
        if token_info:
            await self._cache_token_info(chain_id, identifier, token_info)
            return token_info

        # Try on-chain lookup if it looks like an address
        if len(identifier) == 42 and identifier.startswith("0x"):
            token_info = await self._get_token_from_chain(chain_id, identifier)
            if token_info:
                await self._cache_token_info(chain_id, identifier, token_info)
                return token_info

        return None

    async def _get_native_token_info(self, chain_id: int, symbol: str) -> Dict[str, Any]:
        """Get information for native tokens and common stablecoins."""
        if symbol == "eth":
            return {
                "address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "symbol": "ETH",
                "name": "Ethereum",
                "metadata": {
                    "verified": True,
                    "source": "native",
                    "decimals": 18
                }
            }
        elif symbol == "weth":
            # Different WETH addresses per chain
            weth_addresses = {
                1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                137: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
                10: "0x4200000000000000000000000000000000000006",
                8453: "0x4200000000000000000000000000000000000006",
            }
            return {
                "address": weth_addresses.get(chain_id, ""),
                "symbol": "WETH",
                "name": "Wrapped Ether",
                "metadata": {
                    "verified": True,
                    "source": "native",
                    "decimals": 18
                }
            }
        elif symbol == "usdc":
            # USDC addresses for common chains
            usdc_addresses = {
                1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                42161: "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
                137: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
                10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
                8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            }
            return {
                "address": usdc_addresses.get(chain_id, ""),
                "symbol": "USDC",
                "name": "USDC",
                "metadata": {
                    "verified": True,
                    "source": "token_list",
                    "decimals": 6
                }
            }
        elif symbol == "usdt":
            # USDT addresses for common chains
            usdt_addresses = {
                1: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                42161: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
                137: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
                10: "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
                8453: "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
            }
            return {
                "address": usdt_addresses.get(chain_id, ""),
                "symbol": "USDT",
                "name": "Tether USD",
                "metadata": {
                    "verified": True,
                    "source": "token_list",
                    "decimals": 6
                }
            }
        elif symbol == "dai":
            # DAI addresses for common chains
            dai_addresses = {
                1: "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                42161: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                137: "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
                10: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                8453: "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
            }
            return {
                "address": dai_addresses.get(chain_id, ""),
                "symbol": "DAI",
                "name": "Dai Stablecoin",
                "metadata": {
                    "verified": True,
                    "source": "token_list",
                    "decimals": 18
                }
            }
        return None

    async def _get_token_from_lists(self, chain_id: int, identifier: str) -> Optional[Dict[str, Any]]:
        """Fetch token information from token lists."""
        lists = self.token_lists.get(chain_id, [])
        
        async with aiohttp.ClientSession() as session:
            for list_url in lists:
                try:
                    async with session.get(list_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            tokens = data.get("tokens", [])
                            
                            # Search by address or symbol
                            for token in tokens:
                                if (token.get("address", "").lower() == identifier or 
                                    token.get("symbol", "").lower() == identifier):
                                    return {
                                        "address": token["address"],
                                        "symbol": token["symbol"],
                                        "name": token["name"],
                                        "metadata": {
                                            "verified": True,
                                            "source": "token_list",
                                            "decimals": token["decimals"]
                                        }
                                    }
                except Exception:
                    continue
        return None

    async def _get_token_from_chain(self, chain_id: int, address: str) -> Optional[Dict[str, Any]]:
        """Fetch token information directly from the blockchain."""
        if not address.startswith("0x") or len(address) != 42:
            return None

        web3 = self.web3_providers.get(chain_id)
        if not web3:
            return None

        try:
            # Create contract instance
            contract = web3.eth.contract(address=Web3.to_checksum_address(address), abi=ERC20_ABI)

            # Fetch token information concurrently
            name_coro = contract.functions.name().call()
            symbol_coro = contract.functions.symbol().call()
            decimals_coro = contract.functions.decimals().call()

            name, symbol, decimals = await asyncio.gather(
                name_coro, symbol_coro, decimals_coro
            )

            return {
                "address": address,
                "symbol": symbol,
                "name": name,
                "metadata": {
                    "verified": False,  # On-chain tokens are considered unverified by default
                    "source": "on_chain",
                    "decimals": decimals
                }
            }
        except (ContractLogicError, ValueError) as e:
            print(f"Error fetching token info for {address} on chain {chain_id}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching token info: {e}")
            return None

    async def _cache_token_info(self, chain_id: int, identifier: str, token_info: Dict[str, Any]):
        """Cache token information in Redis or memory."""
        key = f"token:{chain_id}:{identifier}"
        
        # Cache in memory
        self.memory_cache[key] = token_info
        
        # Also cache in Redis if available
        if self.use_redis and self.cache:
            try:
                self.cache.setex(
                    key,
                    timedelta(hours=24),  # Cache for 24 hours
                    json.dumps(token_info)
                )
            except Exception as e:
                print(f"Redis cache error: {e}")

    async def get_chain_name(self, chain_id: int) -> str:
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
            324: "zkSync Era",
            59144: "Linea",
            5000: "Mantle",
            81457: "Blast",
            100: "Gnosis",
            7777777: "Zora",
            424: "PGN",
            167004: "Taiko",
            204: "opBNB",
            1101: "Polygon zkEVM",
            2222: "Kava",
            1284: "Moonbeam",
            1285: "Moonriver",
            42220: "Celo",
            250: "Fantom",
            25: "Cronos",
            1313161554: "Aurora",
            1088: "Metis",
            288: "Boba",
            106: "Velas",
            128: "Huobi ECO Chain",
            66: "OKXChain",
            1666600000: "Harmony",
            2001: "Milkomeda",
            2002: "Algrand",
            2222: "Kava",
            42262: "Oasis",
            43114: "Avalanche",
            592: "Astar",
            1030: "Conflux",
            1234: "Step",
            1399: "Polygon zkEVM Testnet",
            80001: "Mumbai",
            421613: "Arbitrum Goerli",
            5: "Goerli",
            11155111: "Sepolia",
            84531: "Base Goerli",
            534351: "Scroll Sepolia",
            167005: "Taiko Jolnir",
            167006: "Taiko Katla"
        }
        return chain_names.get(chain_id, f"Chain {chain_id}")

# Global instance
token_service = TokenService() 