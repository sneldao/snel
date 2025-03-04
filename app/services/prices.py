import os
import logging
import httpx
import json
from fastapi import HTTPException
from typing import Optional, Dict, Tuple, Set, Any, List, Union, TypedDict
import re
from datetime import datetime, timedelta
import asyncio
from eth_utils import is_address, to_checksum_address
from app.config.chains import TOKEN_ADDRESSES, TOKEN_DECIMALS
from app.services.token_service import TokenService
import time

logger = logging.getLogger(__name__)

MORALIS_API_KEY = os.environ.get("MORALIS_API_KEY")
if not MORALIS_API_KEY:
    raise ValueError("MORALIS_API_KEY environment variable is required")

QUICKNODE_API_KEY = os.environ.get("QUICKNODE_API_KEY")
QUICKNODE_ENDPOINT = os.environ.get("QUICKNODE_ENDPOINT")

# Check if SSL verification should be disabled (for development only)
DISABLE_SSL_VERIFY = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"
if DISABLE_SSL_VERIFY and not os.environ.get("SSL_WARNING_SHOWN"):
    logger.warning("⚠️ SECURITY WARNING: SSL certificate verification is disabled in prices.py. This makes your connections less secure and should ONLY be used during development.")
    # Mark that we've shown the warning
    os.environ["SSL_WARNING_SHOWN"] = "true"

# Cache for validated tokens to reduce API calls
# Structure: {(token_id, chain_id): (timestamp, is_valid)}
_token_cache: Dict[Tuple[str, Optional[int]], Tuple[datetime, bool]] = {}
CACHE_DURATION = timedelta(minutes=30)

# Global constants
COINGECKO_ID_MAPPING = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "usdt": "tether",
    "usdc": "usd-coin",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "sol": "solana",
    "matic": "polygon",
    "dot": "polkadot",
    "shib": "shiba-inu",
    "avax": "avalanche-2",
    "link": "chainlink",
    "etc": "ethereum-classic",
    "uni": "uniswap",
    "wbtc": "wrapped-bitcoin",
    "dai": "dai",
    "atom": "cosmos",
    "op": "optimism",
    "arb": "arbitrum"
}

# Cache for token validation results
_token_validation_cache: Dict[str, Dict[str, Any]] = {}

# Global price cache
_price_cache = {}

# Define standard return type for price data
class TokenPriceData(TypedDict, total=False):
    """Standard return type for token price data"""
    price: float
    change_24h: float
    source: str
    timestamp: str
    decimals: int

class PriceService:
    """Service for retrieving token prices from various sources."""
    
    def __init__(self):
        """Initialize the price service."""
        self.coingecko_api_key = os.environ.get("COINGECKO_API_KEY")
        self.moralis_api_key = os.environ.get("MORALIS_API_KEY")
        self.quicknode_api_key = os.environ.get("QUICKNODE_API_KEY")
        self.quicknode_endpoint = os.environ.get("QUICKNODE_ENDPOINT")
        
        # Initialize cache
        self.cache_duration = 300  # 5 minutes in seconds
    
    async def get_token_price(
        self, 
        token_symbol: str, 
        quote_currency: str = "usd",
        chain_id: Optional[int] = None
    ) -> Optional[TokenPriceData]:
        """Get token price from various sources."""
        if not token_symbol:
            return None
        
        # Normalize token symbol
        token_symbol = _normalize_token(token_symbol)
        quote_currency = quote_currency.lower()
        
        # Check cache first
        cache_key = f"{token_symbol}:{quote_currency}:{chain_id or 'default'}"
        cached_data = _get_from_cache(token_symbol, chain_id)
        if cached_data:
            price, decimals = cached_data
            if price is not None:
                return {
                    "price": price,
                    "change_24h": 0.0,  # We don't cache the change
                    "source": "cache",
                    "timestamp": datetime.now().isoformat(),
                    "decimals": decimals
                }
        
        # Get token address from token service
        from app.services.token_service import token_service
        token_info = await token_service.lookup_token(token_symbol, chain_id or 1)
        token_address = token_info[0] if token_info else None
        
        # Try OpenOcean first if we have a token address and chain ID
        if token_address and chain_id:
            price_data = await self._get_price_from_openocean(token_symbol, token_address, chain_id)
            if price_data:
                # Cache the result and return immediately
                _add_to_cache(token_symbol, chain_id, (price_data["price"], price_data["decimals"]))
                return price_data
        
        # Only try other sources if OpenOcean failed or we don't have token address/chain ID
        # For major cryptocurrencies, try CoinGecko
        if token_symbol.lower() in ["btc", "eth", "usdt", "usdc", "dai", "wbtc", "weth"]:
            price_data = await self._get_price_from_coingecko(token_symbol, quote_currency, chain_id)
            if price_data:
                _add_to_cache(token_symbol, chain_id, (price_data["price"], price_data["decimals"]))
                return price_data
        
        # For chain-specific tokens, try Moralis
        if chain_id and token_address:
            price_data = await self._get_price_from_moralis(token_symbol, quote_currency, chain_id)
            if price_data:
                _add_to_cache(token_symbol, chain_id, (price_data["price"], price_data["decimals"]))
                return price_data
        
        # Try CoinGecko as fallback for any token
        price_data = await self._get_price_from_coingecko(token_symbol, quote_currency, chain_id)
        if price_data:
            _add_to_cache(token_symbol, chain_id, (price_data["price"], price_data["decimals"]))
            return price_data
        
        # Try QuickNode as last resort for chain-specific tokens
        if chain_id:
            price_data = await self._get_price_from_quicknode(token_symbol, quote_currency, chain_id)
            if price_data:
                _add_to_cache(token_symbol, chain_id, (price_data["price"], price_data["decimals"]))
                return price_data
        
        return None
    
    async def _get_price_from_coingecko(
        self, 
        token_symbol: str, 
        quote_currency: str,
        chain_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get token price from CoinGecko API."""
        if not self.coingecko_api_key:
            logger.warning("CoinGecko API key not available")
            return None
        
        try:
            # First try to get the token address if available
            from app.services.token_service import token_service
            token_info = await token_service.lookup_token(token_symbol, chain_id or 1)
            token_address = token_info[0] if token_info else None
            
            # Map chain ID to CoinGecko platform ID
            platform_mapping = {
                1: "ethereum",
                56: "binance-smart-chain",
                137: "polygon-pos",
                10: "optimistic-ethereum",
                42161: "arbitrum-one",
                8453: "base",
                534352: "scroll"
            }
            
            headers = {}
            if self.coingecko_api_key:
                headers["x-cg-api-key"] = self.coingecko_api_key
            
            # If we have both token address and chain platform, use the token price endpoint
            if token_address and chain_id and chain_id in platform_mapping:
                platform = platform_mapping[chain_id]
                url = f"https://api.coingecko.com/api/v3/simple/token_price/{platform}"
                params = {
                    "contract_addresses": token_address,
                    "vs_currencies": quote_currency
                }
                
                logger.info(f"Getting price for token {token_symbol} ({token_address}) on {platform} from CoinGecko")
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data and token_address.lower() in data:
                            token_data = data[token_address.lower()]
                            if quote_currency in token_data:
                                price = float(token_data[quote_currency])
                                
                                return {
                                    "price": price,
                                    "change_24h": 0,  # Simple endpoint doesn't provide 24h change
                                    "source": "coingecko",
                                    "timestamp": datetime.now().isoformat(),
                                    "decimals": 18  # Default decimals
                                }
            
            # Fallback to the coin ID-based endpoint
            coin_id = self._map_symbol_to_coingecko_id(token_symbol)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={quote_currency}&include_24hr_change=true"
            
            logger.info(f"Falling back to coin ID lookup for {token_symbol} (ID: {coin_id}) from CoinGecko")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if coin_id in data:
                        coin_data = data[coin_id]
                        price = coin_data.get(quote_currency)
                        change_24h = coin_data.get(f"{quote_currency}_24h_change", 0)
                        
                        if price:
                            return {
                                "price": float(price),
                                "change_24h": float(change_24h) if change_24h else 0,
                                "source": "coingecko",
                                "timestamp": datetime.now().isoformat(),
                                "decimals": 18  # Default decimals
                            }
        
        except Exception as e:
            logger.error(f"Error getting price from CoinGecko: {str(e)}")
        
        return None
    
    async def _get_price_from_moralis(
        self, 
        token_symbol: str, 
        quote_currency: str,
        chain_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get token price from Moralis API."""
        if not self.moralis_api_key:
            return None
        
        try:
            # First try to look up token address by symbol
            from app.services.token_service import token_service
            token_info = await token_service.lookup_token(token_symbol, chain_id or 1)
            
            if not token_info or not token_info[0]:
                logger.warning(f"Could not find token address for {token_symbol}")
                return None
            
            token_address = token_info[0]
            
            # Map chain ID to Moralis chain name
            chain_mapping = {
                1: "eth",
                56: "bsc",
                137: "polygon",
                10: "optimism",
                42161: "arbitrum",
                8453: "base",
                534352: "scroll"
            }
            
            chain = chain_mapping.get(chain_id or 1, "eth")
            
            # Use the correct v2.2 endpoint for token price
            url = f"https://deep-index.moralis.io/api/v2.2/erc20/{token_address}/price"
            params = {"chain": chain}
            headers = {"X-API-Key": self.moralis_api_key}
            
            logger.info(f"Getting price for token {token_symbol} ({token_address}) on chain {chain} from Moralis")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if "usdPrice" in data:
                        price = float(data["usdPrice"])
                        change = float(data.get("24hrPercentChange", 0))
                        
                        return {
                            "price": price,
                            "change_24h": change,
                            "source": "moralis",
                            "timestamp": datetime.now().isoformat(),
                            "decimals": int(data.get("tokenDecimals", 18))
                        }
                else:
                    logger.warning(f"Moralis API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting price from Moralis: {str(e)}")
        
        return None
    
    async def _get_price_from_quicknode(
        self, 
        token_symbol: str, 
        quote_currency: str,
        chain_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get token price from QuickNode API."""
        if not self.quicknode_api_key:
            logger.warning("QuickNode API key not available")
            return None
        
        try:
            # Use QuickNode's token price endpoint
            chain_param = f"&chainId={chain_id}" if chain_id else ""
            url = f"https://api.quicknode.com/token-prices?symbol={token_symbol}{chain_param}"
            
            logger.info(f"Fetching price from QuickNode: {url}")
            
            headers = {"x-api-key": self.quicknode_api_key}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("prices"):
                        price_data = data["prices"][0]
                        price = price_data.get("price")
                        
                        return {
                            "price": price,
                            "change_24h": price_data.get("priceChange24h", 0),
                            "source": "quicknode",
                            "timestamp": datetime.now().isoformat()
                        }
                else:
                    logger.warning(f"QuickNode API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error fetching price from QuickNode: {str(e)}")
        
        return None
    
    def _map_symbol_to_coingecko_id(self, symbol: str) -> str:
        """Map a token symbol to its CoinGecko ID."""
        symbol_mapping = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "usdt": "tether",
            "usdc": "usd-coin",
            "bnb": "binancecoin",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "sol": "solana",
            "matic": "polygon",
            "dot": "polkadot",
            "shib": "shiba-inu",
            "avax": "avalanche-2",
            "link": "chainlink",
            "etc": "ethereum-classic",
            "uni": "uniswap",
            "wbtc": "wrapped-bitcoin",
            "dai": "dai",
            "atom": "cosmos",
            "op": "optimism",
            "arb": "arbitrum"
        }
        
        return symbol_mapping.get(symbol.lower(), symbol.lower())
    
    def _get_token_address(self, symbol: str, chain_id: int) -> Optional[str]:
        """Get token address for a symbol on a specific chain."""
        # Common token addresses by chain
        token_addresses = {
            1: {  # Ethereum
                "usdt": "0xdac17f958d2ee523a2206206994597c13d831ec7",
                "usdc": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "dai": "0x6b175474e89094c44da98b954eedeac495271d0f",
                "weth": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "wbtc": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
            },
            137: {  # Polygon
                "usdt": "0xc2132d05d31c914a87c6611c10748aeb04b58e8f",
                "usdc": "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
                "dai": "0x8f3cf7ad23cd3cadbd9735aff958023239c6a063",
                "weth": "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619",
                "wmatic": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270"
            },
            8453: {  # Base
                "usdc": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "dai": "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
                "weth": "0x4200000000000000000000000000000000000006"
            }
        }
        
        if chain_id in token_addresses and symbol.lower() in token_addresses[chain_id]:
            return token_addresses[chain_id][symbol.lower()]
        
        return None

    async def _get_price_from_openocean(
        self, 
        token_symbol: str,
        token_address: str,
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token price from OpenOcean API."""
        try:
            # Map chain IDs to OpenOcean chain names
            chain_mapping = {
                1: "eth",
                56: "bsc",
                137: "polygon",
                10: "optimism",
                42161: "arbitrum",
                8453: "base",
                534352: "scroll"
            }
            
            chain = chain_mapping.get(chain_id)
            if not chain:
                logger.warning(f"Unsupported chain ID for OpenOcean: {chain_id}")
                return None
            
            url = f"https://open-api.openocean.finance/v4/{chain}/getTokenInfo"
            params = {"tokenAddress": token_address}
            
            logger.info(f"Getting price for token {token_symbol} ({token_address}) on {chain} from OpenOcean")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if "usd" in data and data["usd"]:
                        price = float(data["usd"])
                        decimals = int(data.get("decimals", 18))
                        
                        return {
                            "price": price,
                            "change_24h": 0,  # OpenOcean doesn't provide 24h change
                            "source": "openocean",
                            "timestamp": datetime.now().isoformat(),
                            "decimals": decimals
                        }
                else:
                    logger.warning(f"OpenOcean API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting price from OpenOcean: {str(e)}")
        
        return None

# Export a singleton instance
price_service = PriceService()

def _is_valid_contract_address(token: str) -> bool:
    """Check if the token is a valid Ethereum contract address."""
    try:
        return is_address(token)
    except Exception:
        return False

def _normalize_token(token: str) -> str:
    """Normalize token symbol/name for consistent comparison."""
    return re.sub(r'[^a-zA-Z0-9]', '', token.upper())

def _get_from_cache(token: str, chain_id: Optional[int] = None) -> Optional[Tuple[Optional[float], int]]:
    """Get token price from cache."""
    cache_key = f"{token}:{chain_id or 'none'}"
    if cache_key in _price_cache:
        cache_entry = _price_cache[cache_key]
        # Check if cache entry is still valid (less than 5 minutes old)
        if time.time() - cache_entry["timestamp"] < 300:  # 5 minutes
            return cache_entry["data"]
    return None

def _add_to_cache(token: str, chain_id: Optional[int], data: Tuple[Optional[float], int]) -> None:
    """Add token price to cache."""
    cache_key = f"{token}:{chain_id or 'none'}"
    _price_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }
    # Trim cache if it gets too large
    if len(_price_cache) > 1000:
        # Remove oldest entries
        sorted_keys = sorted(_price_cache.keys(), key=lambda k: _price_cache[k]["timestamp"])
        for key in sorted_keys[:100]:  # Remove oldest 100 entries
            del _price_cache[key]

def _get_chain_name(chain_id: int) -> Optional[str]:
    """Map chain IDs to Moralis chain names."""
    chain_names = {
        1: "eth",
        8453: "base",
        42161: "arbitrum",
        10: "optimism",
        137: "polygon",
        43114: "avalanche",
        534352: "scroll"
    }
    return chain_names.get(chain_id)


def _is_well_known_token(token_id: str) -> bool:
    """Check if a token is well-known."""
    normalized_token = _normalize_token(token_id)
    well_known_tokens = {"ETH", "WETH", "USDC", "USDT", "DAI", "UNI", "LINK", "AAVE", "SNX", "COMP", "SCR", "OP", "ARB", "BASE", "MATIC", "SCROLL"}
    return normalized_token in {_normalize_token(t) for t in well_known_tokens}


def _is_permissive_token(token_id: str) -> bool:
    """Check if a token should be permissively allowed."""
    if token_id.startswith('$'):
        logger.warning(
            f"CAUTION: Allowing unverified token with $ prefix: {token_id}. "
            f"This token has not been validated through standard methods. "
            f"Users should verify the contract address before swapping."
        )
        return True

    if re.match(r'^[A-Za-z0-9]{2,10}$', token_id):
        logger.warning(
            f"CAUTION: Allowing unverified token with valid symbol pattern: {token_id}. "
            f"This token has not been validated through standard methods. "
            f"Users should verify the contract address before swapping."
        )
        return True

    return False

async def get_token_price_moralis(token_address: str, chain_id: int) -> Optional[float]:
    """Get token price from Moralis API."""
    moralis_api_key = os.environ.get("MORALIS_API_KEY")
    if not moralis_api_key:
        logger.warning("Moralis API key not set")
        return None

    # Map chain ID to Moralis chain name
    chain_mapping = {
        1: "eth",
        56: "bsc",
        137: "polygon",
        10: "optimism",
        42161: "arbitrum",
        8453: "base",
        534352: "scroll"
    }
    
    chain = chain_mapping.get(chain_id, "eth")
    
    try:
        # Use the correct v2.2 endpoint for token price
        url = f"https://deep-index.moralis.io/api/v2.2/erc20/{token_address}/price"
        params = {"chain": chain}
        headers = {"X-API-Key": moralis_api_key}
        
        logger.info(f"Getting price for token {token_address} on chain {chain} from Moralis")
        
        async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
            response = await client.get(
                url,
                params=params,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if "usdPrice" in data:
                    price = float(data["usdPrice"])
                    logger.info(f"Got price from Moralis: ${price}")
                    return price
                else:
                    logger.warning(f"Unexpected response format from Moralis: {data}")
            else:
                logger.warning(f"Moralis API error: {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"Error getting price from Moralis: {e}")
    
    return None

async def get_token_price_coingecko(
    token_id: str, 
    token_address: Optional[str] = None,
    chain_id: Optional[int] = None
) -> Optional[float]:
    """Get token price from CoinGecko API."""
    try:
        # If we have token address and chain ID, use the token price endpoint
        if token_address and chain_id:
            # Map chain ID to CoinGecko platform ID
            platform_mapping = {
                1: "ethereum",
                56: "binance-smart-chain",
                137: "polygon-pos",
                10: "optimistic-ethereum",
                42161: "arbitrum-one",
                8453: "base",
                534352: "scroll"
            }
            
            if chain_id in platform_mapping:
                platform = platform_mapping[chain_id]
                url = f"https://api.coingecko.com/api/v3/simple/token_price/{platform}"
                params = {
                    "contract_addresses": token_address,
                    "vs_currencies": "usd"
                }
                
                headers = {}
                if os.environ.get("COINGECKO_API_KEY"):
                    headers["x-cg-api-key"] = os.environ.get("COINGECKO_API_KEY")
                
                logger.info(f"Getting price for token {token_id} ({token_address}) on {platform} from CoinGecko")
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data and token_address.lower() in data:
                            token_data = data[token_address.lower()]
                            if "usd" in token_data:
                                return float(token_data["usd"])
        
        # Fallback to the coin ID-based endpoint
        # Map common symbols to CoinGecko IDs
        if token_id.lower() in COINGECKO_ID_MAPPING:
            coin_id = COINGECKO_ID_MAPPING[token_id.lower()]
        else:
            coin_id = token_id.lower()
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        
        headers = {}
        if os.environ.get("COINGECKO_API_KEY"):
            headers["x-cg-api-key"] = os.environ.get("COINGECKO_API_KEY")
        
        logger.info(f"Falling back to coin ID lookup for {token_id} (ID: {coin_id}) from CoinGecko")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if coin_id in data and "usd" in data[coin_id]:
                    return float(data[coin_id]["usd"])
            else:
                logger.warning(f"CoinGecko API error: {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"Error getting price from CoinGecko: {str(e)}")
    
    return None

async def get_token_price(token_id: str, token_address: Optional[str] = None, chain_id: Optional[int] = None) -> Tuple[Optional[float], int]:
    """
    Get token price from various sources.
    
    Args:
        token_id: Token symbol or ID
        token_address: Optional token contract address
        chain_id: Optional chain ID
        
    Returns:
        Tuple of (price, decimals) where price can be None if not found
    """
    # Normalize token ID
    token_id = _normalize_token(token_id)
    
    # Special case for stablecoins
    stablecoins = {"usdc", "usdt", "dai", "busd", "tusd", "usdp"}
    if token_id.lower() in stablecoins:
        logger.info(f"Using fixed price for stablecoin: {token_id}")
        decimals = 6 if token_id.lower() in {"usdc", "usdt"} else 18
        return (1.0, decimals)
    
    # Check cache first
    cache_key = f"{token_id}:{token_address or 'none'}:{chain_id or 'none'}"
    cached_price = _get_from_cache(cache_key)
    if cached_price is not None:
        logger.info(f"Using cached price for {token_id}: {cached_price}")
        return cached_price
    
    # Default decimals based on token
    default_decimals = 18
    if token_id.lower() in ["btc", "wbtc"]:
        default_decimals = 8
    elif token_id.lower() in ["usdc", "usdt"]:
        default_decimals = 6
    
    # Try CoinGecko first for well-known tokens
    if token_id.lower() in ["btc", "eth", "usdt", "usdc", "dai", "wbtc", "weth"]:
        price = await get_token_price_coingecko(token_id, token_address, chain_id)
        if price is not None:
            _add_to_cache(token_id, chain_id, (price, default_decimals))
            return (price, default_decimals)
    
    # Try Moralis for EVM tokens if we have chain ID
    if chain_id:
        price = await get_token_price_moralis(token_address or token_id, chain_id)
        if price is not None:
            _add_to_cache(token_id, chain_id, (price, default_decimals))
            return (price, default_decimals)
    
    # Try CoinGecko as fallback
    price = await get_token_price_coingecko(token_id, token_address, chain_id)
    if price is not None:
        _add_to_cache(token_id, chain_id, (price, default_decimals))
        return (price, default_decimals)
    
    # If all else fails, return None with default decimals
    logger.warning(f"Could not get price for {token_id}")
    return (None, default_decimals)

async def _validate_with_coingecko(token_id: str) -> bool:
    """Validate token using CoinGecko's search API."""
    variations = [
        token_id,
        token_id.lower(),
        token_id.upper(),
        token_id.capitalize()
    ]

    coingecko_api_key = os.environ.get("COINGECKO_API_KEY")
    
    for variation in variations:
        try:
            # Construct API URL - always use api.coingecko.com as we have a Demo API key
            url = "https://api.coingecko.com/api/v3/search"
            if coingecko_api_key:
                params = {"query": variation, "x_cg_demo_api_key": coingecko_api_key}
            else:
                params = {"query": variation}

            async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
                response = await client.get(
                    url,
                    params=params,
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    coins = data.get("coins", [])

                    # Check both symbol and name matches
                    normalized_query = _normalize_token(variation)
                    for coin in coins:
                        if normalized_query in [
                            _normalize_token(coin["symbol"]),
                            _normalize_token(coin["name"]),
                        ]:
                            return True

                elif response.status_code == 429:  # Rate limit
                    logger.warning("CoinGecko rate limit reached")
                    await asyncio.sleep(1)  # Back off for a second
                    continue

        except Exception as e:
            logger.warning(f"CoinGecko validation attempt failed for {variation}: {e}")
            continue

    return False

async def _validate_with_moralis(token_id: str, chain_id: int) -> bool:
    """Validate token using Moralis APIs."""
    chain_names = {
        1: "eth",
        8453: "base",
        42161: "arbitrum",
        10: "optimism",
        137: "polygon",
        43114: "avalanche",
        534352: "scroll"
    }

    chain = chain_names.get(chain_id)
    if not chain:
        logger.warning(f"Unsupported chain ID for Moralis: {chain_id}")
        return False

    try:
        # Try token metadata endpoint first
        url = "https://deep-index.moralis.io/api/v2.2/erc20/metadata/symbols"
        params = {
            "chain": chain,
            "symbols": [token_id.upper()]
        }

        async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
            response = await client.get(
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "X-API-Key": MORALIS_API_KEY
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return True

            # If metadata lookup fails, try token search
            search_url = "https://deep-index.moralis.io/api/v2.2/erc20/tokens"
            search_params = {
                "chain": chain,
                "q": token_id
            }

            search_response = await client.get(
                search_url,
                params=search_params,
                headers={
                    "Accept": "application/json",
                    "X-API-Key": MORALIS_API_KEY
                },
                timeout=10.0
            )

            if search_response.status_code == 200:
                search_data = search_response.json()
                if search_data and len(search_data) > 0:
                    return True

    except Exception as e:
        logger.warning(f"Moralis validation failed for {token_id}: {e}")

    return False 