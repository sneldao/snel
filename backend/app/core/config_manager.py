"""
Centralized configuration management system for SNEL.

This module provides a single source of truth for all configuration data,
replacing the fragmented config files scattered throughout the codebase.

Core Principles:
- SINGLE SOURCE OF TRUTH: All config data flows through this manager
- DYNAMIC VALIDATION: Real-time verification of addresses and endpoints
- PERFORMANCE: Efficient caching with smart invalidation
- RELIABILITY: Circuit breakers and fallback mechanisms
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import aiohttp
try:
    import aioredis
except ImportError:
    aioredis = None
import os

logger = logging.getLogger(__name__)


class NetworkStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class ProtocolType(Enum):
    DEX = "dex"
    BRIDGE = "bridge"
    AGGREGATOR = "aggregator"


@dataclass
class TokenConfig:
    """Standardized token configuration."""
    id: str
    symbol: str
    name: str
    decimals: int
    addresses: Dict[int, str]  # chain_id -> address
    coingecko_id: Optional[str] = None
    verified: bool = False
    last_verified: Optional[datetime] = None
    price_feeds: Dict[str, str] = field(default_factory=dict)


@dataclass
class ChainConfig:
    """Standardized chain configuration."""
    chain_id: int
    name: str
    display_name: str
    rpc_urls: List[str]
    explorer_url: str
    native_token: str
    status: NetworkStatus = NetworkStatus.HEALTHY
    block_time: float = 12.0  # seconds
    gas_price_gwei: Optional[float] = None
    last_health_check: Optional[datetime] = None
    supported_protocols: Set[str] = field(default_factory=set)


@dataclass
class ProtocolConfig:
    """Standardized protocol configuration."""
    id: str
    name: str
    type: ProtocolType
    supported_chains: Set[int]
    api_endpoints: Dict[str, str]
    contract_addresses: Dict[int, Dict[str, str]]  # chain_id -> {contract_name: address}
    api_keys: Dict[str, str] = field(default_factory=dict)
    rate_limits: Dict[str, int] = field(default_factory=dict)
    status: NetworkStatus = NetworkStatus.HEALTHY
    last_health_check: Optional[datetime] = None


class ConfigurationManager:
    """
    Centralized configuration manager.

    Provides validated, cached, and monitored access to all system configuration.
    Replaces fragmented config files with a single, reliable source of truth.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None

        # In-memory caches
        self._tokens: Dict[str, TokenConfig] = {}
        self._chains: Dict[int, ChainConfig] = {}
        self._protocols: Dict[str, ProtocolConfig] = {}

        # Cache control
        self._last_token_refresh: Optional[datetime] = None
        self._last_chain_refresh: Optional[datetime] = None
        self._last_protocol_refresh: Optional[datetime] = None

        # Health monitoring
        self._health_check_interval = timedelta(minutes=5)
        self._cache_ttl = timedelta(hours=1)

        # HTTP session for validation
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize the configuration manager."""
        logger.info("Initializing Configuration Manager")

        # Initialize Redis connection
        try:
            if aioredis:
                self.redis = aioredis.from_url(self.redis_url)
                await self.redis.ping()
                logger.info("Redis connection established")
            else:
                logger.warning("aioredis not available. Operating without cache.")
                self.redis = None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Operating without cache.")
            self.redis = None

        # Initialize HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

        # Load initial configuration
        await self._load_initial_config()

        # Start background health checks
        asyncio.create_task(self._health_check_loop())

        logger.info("Configuration Manager initialized successfully")

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
        if self.redis:
            await self.redis.close()

    # Token Management
    async def get_token(self, token_id: str) -> Optional[TokenConfig]:
        """Get token configuration by ID."""
        await self._ensure_tokens_loaded()
        return self._tokens.get(token_id)

    async def get_token_by_symbol(self, symbol: str) -> Optional[TokenConfig]:
        """Get token configuration by symbol."""
        await self._ensure_tokens_loaded()
        for token in self._tokens.values():
            if token.symbol.upper() == symbol.upper():
                return token
        return None

    async def get_token_address(self, token_id: str, chain_id: int) -> Optional[str]:
        """Get token address for specific chain."""
        token = await self.get_token(token_id)
        if token:
            return token.addresses.get(chain_id)
        return None

    async def get_all_tokens(self) -> Dict[str, TokenConfig]:
        """Get all token configurations."""
        await self._ensure_tokens_loaded()
        return self._tokens.copy()

    # Chain Management
    async def get_chain(self, chain_id: int) -> Optional[ChainConfig]:
        """Get chain configuration by ID."""
        await self._ensure_chains_loaded()
        return self._chains.get(chain_id)

    async def get_healthy_chains(self) -> List[ChainConfig]:
        """Get all healthy chain configurations."""
        await self._ensure_chains_loaded()
        return [chain for chain in self._chains.values()
                if chain.status == NetworkStatus.HEALTHY]

    async def get_supported_chains(self, protocol_id: str) -> List[ChainConfig]:
        """Get chains supported by a specific protocol."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol:
            return []

        await self._ensure_chains_loaded()
        return [self._chains[chain_id] for chain_id in protocol.supported_chains
                if chain_id in self._chains and self._chains[chain_id].status == NetworkStatus.HEALTHY]

    # Protocol Management
    async def get_protocol(self, protocol_id: str) -> Optional[ProtocolConfig]:
        """Get protocol configuration by ID."""
        await self._ensure_protocols_loaded()
        return self._protocols.get(protocol_id)

    async def get_healthy_protocols(self) -> List[ProtocolConfig]:
        """Get all healthy protocol configurations."""
        await self._ensure_protocols_loaded()
        return [protocol for protocol in self._protocols.values()
                if protocol.status == NetworkStatus.HEALTHY]

    async def is_protocol_supported(self, protocol_id: str, chain_id: int) -> bool:
        """Check if protocol is supported on chain."""
        protocol = await self.get_protocol(protocol_id)
        if not protocol:
            return False
        return chain_id in protocol.supported_chains

    # Configuration Loading
    async def _load_initial_config(self):
        """Load initial configuration from various sources."""
        logger.info("Loading initial configuration")

        # Load from cache if available
        if self.redis:
            await self._load_from_cache()

        # Load from files if cache is empty
        if not self._tokens:
            await self._load_tokens_from_file()
        if not self._chains:
            await self._load_chains_from_file()
        if not self._protocols:
            await self._load_protocols_from_file()

        # Validate loaded configuration
        await self._validate_configuration()

        logger.info(f"Loaded {len(self._tokens)} tokens, {len(self._chains)} chains, {len(self._protocols)} protocols")

    async def _load_tokens_from_file(self):
        """Load token configuration from file."""
        # USDC - The most important token for Circle integration
        usdc = TokenConfig(
            id="usdc",
            symbol="USDC",
            name="USD Coin",
            decimals=6,
            addresses={
                1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",      # Ethereum
                42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",   # Arbitrum
                137: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",     # Polygon
                10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",      # Optimism
                8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",    # Base
                43114: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",   # Avalanche
                59144: "0x176211869cA2b568f2A7D4EE941E073a821EE1ff",   # Linea
                480: "0x79A02482A880bCE3F13e09Da970dC34db4CD24d1",     # World Chain
                146: "0x29219dd400f2Bf60E5a23d13Be72B486D4038894",     # Sonic
            },
            coingecko_id="usd-coin",
            verified=True
        )

        # WETH - Core trading pair
        weth = TokenConfig(
            id="weth",
            symbol="WETH",
            name="Wrapped Ethereum",
            decimals=18,
            addresses={
                1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",      # Ethereum
                42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",   # Arbitrum
                137: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",     # Polygon
                10: "0x4200000000000000000000000000000000000006",      # Optimism
                8453: "0x4200000000000000000000000000000000000006",    # Base
                43114: "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",   # Avalanche
            },
            coingecko_id="weth",
            verified=True
        )

        # ETH (native)
        eth = TokenConfig(
            id="eth",
            symbol="ETH",
            name="Ethereum",
            decimals=18,
            addresses={
                1: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",      # Native ETH placeholder
                42161: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                10: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                8453: "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            },
            coingecko_id="ethereum",
            verified=True
        )

        self._tokens = {
            "usdc": usdc,
            "weth": weth,
            "eth": eth,
        }

    async def _load_chains_from_file(self):
        """Load chain configuration from file."""
        chains = [
            ChainConfig(
                chain_id=1,
                name="ethereum",
                display_name="Ethereum",
                rpc_urls=[
                    "https://eth.llamarpc.com",
                    "https://ethereum.publicnode.com",
                    "https://eth-mainnet.public.blastapi.io"
                ],
                explorer_url="https://etherscan.io",
                native_token="ETH",
                block_time=12.0,
                supported_protocols={"0x", "uniswap", "axelar", "cctp_v2"}
            ),
            ChainConfig(
                chain_id=8453,
                name="base",
                display_name="Base",
                rpc_urls=[
                    "https://base.llamarpc.com",
                    "https://base-mainnet.public.blastapi.io"
                ],
                explorer_url="https://basescan.org",
                native_token="ETH",
                block_time=2.0,
                supported_protocols={"0x", "uniswap", "cctp_v2"}
            ),
            ChainConfig(
                chain_id=42161,
                name="arbitrum",
                display_name="Arbitrum One",
                rpc_urls=[
                    "https://arbitrum.llamarpc.com",
                    "https://arbitrum-one.publicnode.com"
                ],
                explorer_url="https://arbiscan.io",
                native_token="ETH",
                block_time=0.25,
                supported_protocols={"0x", "uniswap", "axelar", "cctp_v2"}
            ),
            ChainConfig(
                chain_id=137,
                name="polygon",
                display_name="Polygon",
                rpc_urls=[
                    "https://polygon.llamarpc.com",
                    "https://polygon-mainnet.public.blastapi.io"
                ],
                explorer_url="https://polygonscan.com",
                native_token="MATIC",
                block_time=2.0,
                supported_protocols={"0x", "uniswap", "axelar", "cctp_v2"}
            ),
            ChainConfig(
                chain_id=43114,
                name="avalanche",
                display_name="Avalanche",
                rpc_urls=[
                    "https://api.avax.network/ext/bc/C/rpc",
                    "https://avalanche.public-rpc.com"
                ],
                explorer_url="https://snowtrace.io",
                native_token="AVAX",
                block_time=2.0,
                supported_protocols={"0x", "uniswap", "axelar", "cctp_v2"}
            ),
            ChainConfig(
                chain_id=59144,
                name="linea",
                display_name="Linea",
                rpc_urls=[
                    "https://rpc.linea.build",
                    "https://linea-mainnet.public.blastapi.io"
                ],
                explorer_url="https://lineascan.build",
                native_token="ETH",
                block_time=1.0,
                supported_protocols={"axelar", "cctp_v2"}
            ),
            ChainConfig(
                chain_id=480,
                name="worldchain",
                display_name="World Chain",
                rpc_urls=[
                    "https://worldchain-mainnet.g.alchemy.com/public"
                ],
                explorer_url="https://worldscan.org",
                native_token="ETH",
                block_time=2.0,
                supported_protocols={"cctp_v2"}
            ),
            ChainConfig(
                chain_id=146,
                name="sonic",
                display_name="Sonic",
                rpc_urls=[
                    "https://rpc.soniclabs.com"
                ],
                explorer_url="https://sonicscan.org",
                native_token="S",
                block_time=1.0,
                supported_protocols={"cctp_v2"}
            ),
        ]

        self._chains = {chain.chain_id: chain for chain in chains}

    async def _load_protocols_from_file(self):
        """Load protocol configuration from file."""
        # 0x Protocol
        zerox = ProtocolConfig(
            id="0x",
            name="0x Protocol",
            type=ProtocolType.AGGREGATOR,
            supported_chains={1, 137, 42161, 10, 8453, 43114, 59144},
            api_endpoints={
                "1": "https://api.0x.org",
                "137": "https://polygon.api.0x.org",
                "42161": "https://arbitrum.api.0x.org",
                "10": "https://optimism.api.0x.org",
                "8453": "https://base.api.0x.org",
                "43114": "https://avalanche.api.0x.org",
                "59144": "https://linea.api.0x.org",
            },
            contract_addresses={},  # 0x uses API endpoints, not direct contracts
            api_keys={"default": os.getenv("ZEROX_API_KEY", "")},
            rate_limits={"requests_per_minute": 1000}
        )

        # Uniswap
        uniswap = ProtocolConfig(
            id="uniswap",
            name="Uniswap V3",
            type=ProtocolType.DEX,
            supported_chains={1, 137, 42161, 10, 8453},
            api_endpoints={},  # Uses direct contract calls
            contract_addresses={
                1: {
                    "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                    "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                    "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
                },
                8453: {
                    "router": "0x2626664c2603336E57B271c5C0b26F421741e481",
                    "quoter": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
                    "factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
                },
                42161: {
                    "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                    "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                    "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
                }
            },
            rate_limits={"rpc_calls_per_second": 10}
        )

        # Axelar
        axelar = ProtocolConfig(
            id="axelar",
            name="Axelar Network",
            type=ProtocolType.BRIDGE,
            supported_chains={1, 137, 42161, 10, 8453, 43114, 59144},
            api_endpoints={
                "mainnet": "https://api.axelar.dev",
                "lcd": "https://axelar-lcd.quickapi.com"
            },
            contract_addresses={
                # Gateway contracts
                1: {"gateway": "0x4F4495243837681061C4743b74B3eEdf548D56A5"},
                42161: {"gateway": "0xe432150cce91c13a887f7D836923d5597adD8E31"},
                137: {"gateway": "0x6f015F16De9fC8791b234eF68D486d2bF203FBA8"},
                8453: {"gateway": "0xe432150cce91c13a887f7D836923d5597adD8E31"},
            },
            rate_limits={"requests_per_minute": 600}
        )

        # Circle CCTP V2
        cctp_v2 = ProtocolConfig(
            id="cctp_v2",
            name="Circle CCTP V2",
            type=ProtocolType.BRIDGE,
            supported_chains={1, 42161, 8453, 137, 10, 43114, 59144, 480, 146},
            api_endpoints={
                "mainnet": os.getenv("CIRCLE_CCTP_API_URL", "https://api.circle.com/v1/w3s"),
                "attestation": "https://iris-api.circle.com"
            },
            contract_addresses={
                # TokenMessenger contracts for CCTP V2
                1: {
                    "token_messenger": "0xBd3fa81B58Ba92a82136038B25aDec7066af3155",
                    "message_transmitter": "0x0a992d191DEeC32aFe36203Ad87D7d289a738F81",
                    "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
                },
                42161: {
                    "token_messenger": "0x19330d10D9Cc8751218eaf51E8885D058642E08A",
                    "message_transmitter": "0xC30362313FBBA5cf9163F0bb16a0e01f01A896ca",
                    "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
                },
                8453: {
                    "token_messenger": "0x1682Ae6375C4E4A97e4B583BC394c861A46D8962",
                    "message_transmitter": "0xAD09780d193884d503182aD4588450C416D6F9D4",
                    "usdc": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
                },
                137: {
                    "token_messenger": "0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE",
                    "message_transmitter": "0xF3be9355363857F3e001be68856A2f96b4C39Ba9",
                    "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
                },
                10: {
                    "token_messenger": "0x2B4069517957735bE00ceE0fadAE88a26365528f",
                    "message_transmitter": "0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8",
                    "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
                },
                43114: {
                    "token_messenger": "0x6B25532e1060CE10cc3B0A99e5683b91BFDe6982",
                    "message_transmitter": "0x8186359aF5F57FbB40c6b14A588d2A59C0C29880",
                    "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
                },
                59144: {
                    "token_messenger": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
                    "message_transmitter": "0x4C1A2e70A006C29079c7d4073d8C3c7b8C5D8686",
                    "usdc": "0x176211869cA2b568f2A7D4EE941E073a821EE1ff"
                },
                480: {
                    "token_messenger": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
                    "message_transmitter": "0x4C1A2e70A006C29079c7d4073d8C3c7b8C5D8686",
                    "usdc": "0x79A02482A880bCE3F13e09Da970dC34db4CD24d1"
                },
                146: {
                    "token_messenger": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
                    "message_transmitter": "0x4C1A2e70A006C29079c7d4073d8C3c7b8C5D8686",
                    "usdc": "0x29219dd400f2Bf60E5a23d13Be72B486D4038894"
                }
            },
            api_keys={"default": os.getenv("CIRCLE_API_KEY", "")},
            rate_limits={"requests_per_minute": 600}
        )

        self._protocols = {
            "0x": zerox,
            "uniswap": uniswap,
            "axelar": axelar,
            "cctp_v2": cctp_v2,
        }

    async def _validate_configuration(self):
        """Validate all loaded configuration."""
        logger.info("Validating configuration")

        # Validate token addresses
        for token_id, token in self._tokens.items():
            for chain_id, address in token.addresses.items():
                if not await self._is_valid_address(address, chain_id):
                    logger.warning(f"Invalid token address for {token_id} on chain {chain_id}: {address}")

        # Validate chain RPCs
        for chain_id, chain in self._chains.items():
            healthy_rpcs = []
            for rpc_url in chain.rpc_urls:
                if await self._is_healthy_rpc(rpc_url, chain_id):
                    healthy_rpcs.append(rpc_url)
            if healthy_rpcs:
                chain.rpc_urls = healthy_rpcs
                chain.status = NetworkStatus.HEALTHY
            else:
                chain.status = NetworkStatus.OFFLINE
                logger.warning(f"No healthy RPCs found for chain {chain_id}")

        # Validate protocol endpoints
        for protocol_id, protocol in self._protocols.items():
            if await self._is_healthy_protocol(protocol):
                protocol.status = NetworkStatus.HEALTHY
            else:
                protocol.status = NetworkStatus.OFFLINE
                logger.warning(f"Protocol {protocol_id} appears to be offline")

    async def _is_valid_address(self, address: str, chain_id: int) -> bool:
        """Validate if an address is a valid contract address."""
        if not address or len(address) != 42 or not address.startswith("0x"):
            return False

        # For ETH native token placeholder
        if address == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
            return True

        # TODO: Add actual contract validation via RPC call
        return True

    async def _is_healthy_rpc(self, rpc_url: str, expected_chain_id: int) -> bool:
        """Check if RPC endpoint is healthy."""
        try:
            if not self.session:
                return False

            payload = {
                "jsonrpc": "2.0",
                "method": "eth_chainId",
                "params": [],
                "id": 1
            }

            async with self.session.post(rpc_url, json=payload) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                chain_id = int(data.get("result", "0x0"), 16)
                return chain_id == expected_chain_id

        except Exception as e:
            logger.debug(f"RPC health check failed for {rpc_url}: {e}")
            return False

    async def _is_healthy_protocol(self, protocol: ProtocolConfig) -> bool:
        """Check if protocol endpoints are healthy."""
        if protocol.type == ProtocolType.DEX:
            # For DEX protocols, check if we have valid contract addresses
            return len(protocol.contract_addresses) > 0

        # For API-based protocols, check endpoint health
        for endpoint in protocol.api_endpoints.values():
            try:
                if not self.session:
                    continue

                async with self.session.get(f"{endpoint}/health") as response:
                    if response.status == 200:
                        return True
            except:
                continue

        return False

    # Cache Management
    async def _ensure_tokens_loaded(self):
        """Ensure tokens are loaded and fresh."""
        if (not self._tokens or
            not self._last_token_refresh or
            datetime.now() - self._last_token_refresh > self._cache_ttl):
            await self._load_tokens_from_file()
            self._last_token_refresh = datetime.now()

    async def _ensure_chains_loaded(self):
        """Ensure chains are loaded and fresh."""
        if (not self._chains or
            not self._last_chain_refresh or
            datetime.now() - self._last_chain_refresh > self._cache_ttl):
            await self._load_chains_from_file()
            self._last_chain_refresh = datetime.now()

    async def _ensure_protocols_loaded(self):
        """Ensure protocols are loaded and fresh."""
        if (not self._protocols or
            not self._last_protocol_refresh or
            datetime.now() - self._last_protocol_refresh > self._cache_ttl):
            await self._load_protocols_from_file()
            self._last_protocol_refresh = datetime.now()

    async def _load_from_cache(self):
        """Load configuration from Redis cache."""
        if not self.redis:
            return

        try:
            # Load tokens
            tokens_data = await self.redis.get("config:tokens")
            if tokens_data:
                tokens_dict = json.loads(tokens_data)
                self._tokens = {k: TokenConfig(**v) for k, v in tokens_dict.items()}

            # Load chains
            chains_data = await self.redis.get("config:chains")
            if chains_data:
                chains_dict = json.loads(chains_data)
                self._chains = {int(k): ChainConfig(**v) for k, v in chains_dict.items()}

            # Load protocols
            protocols_data = await self.redis.get("config:protocols")
            if protocols_data:
                protocols_dict = json.loads(protocols_data)
                self._protocols = {k: ProtocolConfig(**v) for k, v in protocols_dict.items()}

        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")

    async def _save_to_cache(self):
        """Save configuration to Redis cache."""
        if not self.redis:
            return

        try:
            # Save tokens
            tokens_dict = {k: v.__dict__ for k, v in self._tokens.items()}
            await self.redis.setex("config:tokens", 3600, json.dumps(tokens_dict, default=str))

            # Save chains
            chains_dict = {k: v.__dict__ for k, v in self._chains.items()}
            await self.redis.setex("config:chains", 3600, json.dumps(chains_dict, default=str))

            # Save protocols
            protocols_dict = {k: v.__dict__ for k, v in self._protocols.items()}
            await self.redis.setex("config:protocols", 3600, json.dumps(protocols_dict, default=str))

        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval.total_seconds())
                await self._validate_configuration()
                await self._save_to_cache()
                logger.debug("Configuration health check completed")
            except Exception as e:
                logger.error(f"Health check failed: {e}")


# Global instance
config_manager = ConfigurationManager()

# Convenience functions for backward compatibility
async def get_token_address(symbol: str, chain_id: int) -> Optional[str]:
    """Get token address by symbol and chain ID."""
    token = await config_manager.get_token_by_symbol(symbol)
    if token:
        return token.addresses.get(chain_id)
    return None

async def is_protocol_supported(protocol_id: str, chain_id: int) -> bool:
    """Check if protocol is supported on chain."""
    return await config_manager.is_protocol_supported(protocol_id, chain_id)

async def get_protocol_config(protocol_id: str) -> Optional[ProtocolConfig]:
    """Get protocol configuration."""
    return await config_manager.get_protocol(protocol_id)
