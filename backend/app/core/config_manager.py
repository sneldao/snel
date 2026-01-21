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
from app.config.tokens import COMMON_TOKENS
from app.config.chains import CHAINS
from app.config.protocols import PROTOCOLS, ProtocolType as CentralProtocolType

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

        # Validate loaded configuration (run in background to avoid startup delays)
        try:
            asyncio.create_task(self._validate_configuration())
        except Exception as e:
            logger.warning(f"Failed to schedule validation: {e}")

        logger.info(f"Loaded {len(self._tokens)} tokens, {len(self._chains)} chains, {len(self._protocols)} protocols")

    async def _load_tokens_from_file(self):
        """Load token configuration from central COMMON_TOKENS config."""
        token_configs = {}
        for chain_id, tokens in COMMON_TOKENS.items():
            for symbol, info in tokens.items():
                token_id = symbol.lower()
                if token_id not in token_configs:
                    token_configs[token_id] = TokenConfig(
                        id=token_id,
                        symbol=info["symbol"],
                        name=info["name"],
                        decimals=info["decimals"],
                        addresses={},
                        verified=info.get("verified", False)
                    )
                token_configs[token_id].addresses[chain_id] = info["address"]
        self._tokens = token_configs

    async def _load_chains_from_file(self):
        """Load chain configuration from central CHAINS config."""
        self._chains = {
            cid: ChainConfig(
                chain_id=cid,
                name=cinfo.name.lower().replace(" ", ""),
                display_name=cinfo.name,
                rpc_urls=[cinfo.rpc_url] if cinfo.rpc_url else [],
                explorer_url=cinfo.explorer_url or "",
                native_token=getattr(cinfo, "native_token", "ETH"), # Handle missing field
                supported_protocols=set(cinfo.supported_protocols or [])
            )
            for cid, cinfo in CHAINS.items()
        }

    async def _load_protocols_from_file(self):
        """Load protocol configuration from central PROTOCOLS config."""
        self._protocols = {
            pid: ProtocolConfig(
                id=pid,
                name=pinfo.name,
                type=ProtocolType(pinfo.type.value),
                supported_chains=pinfo.supported_chains,
                api_endpoints=pinfo.api_endpoints,
                contract_addresses=pinfo.contract_addresses,
                api_keys={"default": os.getenv(f"{pid.upper()}_API_KEY", "")}
            )
            for pid, pinfo in PROTOCOLS.items()
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
