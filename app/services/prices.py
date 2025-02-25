import os
import logging
import httpx
import json
from fastapi import HTTPException
from typing import Optional, Dict, Tuple, Set, Any, List
import re
from datetime import datetime, timedelta
import asyncio
from eth_utils import is_address, to_checksum_address
from app.config.chains import TOKEN_ADDRESSES
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)

MORALIS_API_KEY = os.environ.get("MORALIS_API_KEY")
if not MORALIS_API_KEY:
    raise ValueError("MORALIS_API_KEY environment variable is required")

QUICKNODE_API_KEY = os.environ.get("QUICKNODE_API_KEY")
QUICKNODE_ENDPOINT = os.environ.get("QUICKNODE_ENDPOINT")

# Check if SSL verification should be disabled (for development only)
DISABLE_SSL_VERIFY = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"
if DISABLE_SSL_VERIFY:
    logger.warning("SSL certificate verification is disabled in prices.py. This should only be used in development.")

# Cache for validated tokens to reduce API calls
# Structure: {(token_id, chain_id): (timestamp, is_valid)}
_token_cache: Dict[Tuple[str, Optional[int]], Tuple[datetime, bool]] = {}
CACHE_DURATION = timedelta(minutes=30)

# Cache for token validation results
_token_validation_cache: Dict[str, Dict[str, Any]] = {}

def _is_valid_contract_address(token: str) -> bool:
    """Check if the token is a valid Ethereum contract address."""
    try:
        return is_address(token)
    except Exception:
        return False

def _normalize_token(token: str) -> str:
    """Normalize token symbol/name for consistent comparison."""
    return re.sub(r'[^a-zA-Z0-9]', '', token.upper())

def _get_from_cache(token: str, chain_id: Optional[int] = None) -> Optional[bool]:
    """Get token validation result from cache if available and not expired."""
    cache_key = (_normalize_token(token), chain_id)
    if cache_key in _token_cache:
        timestamp, is_valid = _token_cache[cache_key]
        if datetime.now() - timestamp < CACHE_DURATION:
            return is_valid
        del _token_cache[cache_key]
    return None

def _add_to_cache(token: str, chain_id: Optional[int], is_valid: bool) -> None:
    """Add token validation result to cache."""
    cache_key = (_normalize_token(token), chain_id)
    _token_cache[cache_key] = (datetime.now(), is_valid)

async def get_token_metadata(token_address: str, chain_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get token metadata from Moralis, with fallbacks to CoinGecko and QuickNode."""
    if not _is_valid_contract_address(token_address):
        return None
        
    try:
        if not chain_id:
            return None
            
        # Map chain IDs to Moralis chain names
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
            return None
            
        # Try Moralis first
        try:
            async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
                response = await client.get(
                    f"https://deep-index.moralis.io/api/v2.2/erc20/metadata",
                    params={
                        "chain": chain,
                        "addresses": [token_address]
                    },
                    headers={
                        "Accept": "application/json",
                        "X-API-Key": MORALIS_API_KEY
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        logger.info(f"Got token metadata from Moralis: {data[0]}")
                        return data[0]
                else:
                    logger.warning(f"Moralis metadata request failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"Failed to get token metadata from Moralis: {e}")
        
        # Fallback to CoinGecko
        try:
            async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
                response = await client.get(
                    f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{token_address}",
                    headers={"x-cg-demo-api-key": os.environ.get("COINGECKO_API_KEY", "")}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Got token metadata from CoinGecko: {data}")
                    return {
                        "address": token_address,
                        "symbol": data.get("symbol", "").upper(),
                        "name": data.get("name", "Unknown Token"),
                        "decimals": 18  # Default to 18 for ERC20
                    }
                else:
                    logger.warning(f"CoinGecko metadata request failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"Failed to get token metadata from CoinGecko: {e}")
        
        # Fallback to QuickNode if available
        if QUICKNODE_API_KEY and QUICKNODE_ENDPOINT and chain_id in [1, 8453, 42161, 10, 137, 43114, 534352]:
            try:
                # Use QuickNode's RPC endpoint to get token metadata
                async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
                    # Prepare JSON-RPC request for token metadata
                    payload = {
                        "id": 1,
                        "jsonrpc": "2.0",
                        "method": "qn_getTokenMetadataByContractAddress",
                        "params": {
                            "contract": token_address
                        }
                    }
                    
                    response = await client.post(
                        QUICKNODE_ENDPOINT,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "result" in data and data["result"]:
                            result = data["result"]
                            logger.info(f"Got token metadata from QuickNode: {result}")
                            return {
                                "address": token_address,
                                "symbol": result.get("symbol", "").upper(),
                                "name": result.get("name", "Unknown Token"),
                                "decimals": int(result.get("decimals", 18))
                            }
                    else:
                        logger.warning(f"QuickNode metadata request failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"Failed to get token metadata from QuickNode: {e}")
                
    except Exception as e:
        logger.warning(f"Failed to get token metadata: {e}")
        
    return None

async def get_token_price_moralis(token_address: str, chain_id: int) -> float:
    """Get token price from Moralis."""
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
        raise ValueError(f"Unsupported chain ID: {chain_id}")
        
    url = f"https://deep-index.moralis.io/api/v2.2/erc20/{token_address}/price"
    params = {"chain": chain}
    
    try:
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
            
            if response.status_code != 200:
                logger.error(f"Moralis API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch price data: {response.text}"
                )
                
            data = response.json()
            if "usdPrice" not in data:
                raise ValueError(f"No price data found for token {token_address}")
                
            price = float(data["usdPrice"])
            logger.info(f"Got price from Moralis for {token_address}: ${price}")
            return price
            
    except httpx.TimeoutError:
        logger.error("Timeout fetching price from Moralis")
        raise HTTPException(
            status_code=504,
            detail="Timeout fetching price data. Please try again."
        )
    except Exception as e:
        logger.error(f"Error fetching price from Moralis: {e}")
        raise ValueError(f"Failed to get price: {str(e)}")

async def get_token_price_coingecko(token_id: str) -> float:
    """Get token price from CoinGecko."""
    token_mapping = {
        "ETH": "ethereum",
        "USDC": "usd-coin",
        "UNI": "uniswap",
        # Add more tokens as needed
    }
    
    if token_id not in token_mapping:
        raise ValueError(f"Unsupported token: {token_id}")
        
    coin_id = token_mapping[token_id]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    
    try:
        async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
            response = await client.get(
                url,
                headers={
                    "x-cg-demo-api-key": os.environ["COINGECKO_API_KEY"]
                },
                timeout=10.0
            )
            
            if response.status_code == 429:  # Rate limit exceeded
                logger.warning("CoinGecko rate limit exceeded")
                return None  # Allow fallback to Moralis
                
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                return None  # Allow fallback to Moralis
                
            data = response.json()
            
            # Special case for USDC which should always be ~$1
            if token_id == "USDC":
                return 1.0
                
            if coin_id not in data or "usd" not in data[coin_id]:
                logger.error(f"Unexpected response format: {data}")
                return None  # Allow fallback to Moralis
                
            price = data[coin_id]["usd"]
            logger.info(f"Got price from CoinGecko for {token_id}: ${price}")
            return price
            
    except Exception as e:
        logger.error(f"Error fetching price from CoinGecko: {e}")
        return None  # Allow fallback to Moralis

async def get_token_price(token_id: str, token_address: Optional[str] = None, chain_id: Optional[int] = None) -> Tuple[float, int]:
    """Get token price using CoinGecko with Moralis as fallback."""
    # Try CoinGecko first for well-known tokens
    try:
        price = await get_token_price_coingecko(token_id)
        if price is not None:
            return price, 18  # Most tokens use 18 decimals
    except Exception as e:
        logger.warning(f"CoinGecko price fetch failed: {e}")
    
    # Fallback to Moralis if we have the token address and chain ID
    if token_address and chain_id:
        try:
            # Get token metadata first for decimals
            metadata = await get_token_metadata(token_address, chain_id)
            decimals = int(metadata.get("decimals", 18))
            
            # Then get the price
            price = await get_token_price_moralis(token_address, chain_id)
            return price, decimals
        except Exception as e:
            logger.error(f"Moralis price fetch failed: {e}")
            raise ValueError(f"Failed to get price for {token_id}: {str(e)}")
    else:
        raise ValueError(f"Token {token_id} not found on CoinGecko and no token address provided for Moralis fallback")

async def validate_token(token_id: str, chain_id: Optional[int] = None) -> bool:
    """
    Validate if a token exists using multiple methods:
    1. Check if it's a valid contract address
    2. Check cache
    3. Check well-known tokens
    4. Try CoinGecko
    5. Try Moralis
    6. Try QuickNode
    7. Be permissive with $ prefixed tokens
    
    This function is intentionally permissive to allow users to swap any token
    that exists on the blockchain. Safety measures are implemented at the UI level
    by showing users the contract address and advising them to verify before swapping.
    """
    logger.info(f"Validating token: {token_id} for chain {chain_id}")
    
    # First, check if it's a valid contract address
    if _is_valid_contract_address(token_id):
        logger.info(f"Token {token_id} is a valid contract address")
        return True
    
    # Check cache
    cached_result = _get_from_cache(token_id, chain_id)
    if cached_result is not None:
        logger.info(f"Found cached validation result for {token_id}: {cached_result}")
        return cached_result
    
    # Check well-known tokens
    normalized_token = _normalize_token(token_id)
    well_known_tokens = {"ETH", "WETH", "USDC", "USDT", "DAI", "UNI", "LINK", "AAVE", "SNX", "COMP", "SCR", "OP", "ARB", "BASE", "MATIC", "SCROLL"}
    if normalized_token in {_normalize_token(t) for t in well_known_tokens}:
        logger.info(f"Token {token_id} is a well-known token")
        _add_to_cache(token_id, chain_id, True)
        return True
    
    # Try CoinGecko first
    try:
        coingecko_valid = await _validate_with_coingecko(token_id)
        if coingecko_valid:
            logger.info(f"Token {token_id} validated by CoinGecko")
            _add_to_cache(token_id, chain_id, True)
            return True
    except Exception as e:
        logger.warning(f"CoinGecko validation failed for {token_id}: {e}")
    
    # Try Moralis as fallback if chain_id is provided
    if chain_id:
        try:
            moralis_valid = await _validate_with_moralis(token_id, chain_id)
            if moralis_valid:
                logger.info(f"Token {token_id} validated by Moralis")
                _add_to_cache(token_id, chain_id, True)
                return True
        except Exception as e:
            logger.warning(f"Moralis validation failed for {token_id}: {e}")
    
    # Try QuickNode as another fallback if chain_id is provided
    if chain_id and QUICKNODE_API_KEY and QUICKNODE_ENDPOINT:
        try:
            quicknode_valid = await _validate_with_quicknode(token_id, chain_id)
            if quicknode_valid:
                logger.info(f"Token {token_id} validated by QuickNode")
                _add_to_cache(token_id, chain_id, True)
                return True
        except Exception as e:
            logger.warning(f"QuickNode validation failed for {token_id}: {e}")
    
    # If token starts with $ or has other special formatting, try to clean it and validate again
    if any(c in token_id for c in "$_."):
        clean_token = ''.join(c for c in token_id if c.isalnum())
        logger.info(f"Trying validation with cleaned token: {clean_token}")
        
        # Check if cleaned token is in well-known tokens
        if _normalize_token(clean_token) in {_normalize_token(t) for t in well_known_tokens}:
            logger.info(f"Cleaned token {clean_token} is a well-known token")
            _add_to_cache(token_id, chain_id, True)
            return True
            
        # Try external validation with cleaned token
        try:
            coingecko_valid = await _validate_with_coingecko(clean_token)
            if coingecko_valid:
                logger.info(f"Cleaned token {clean_token} validated by CoinGecko")
                _add_to_cache(token_id, chain_id, True)
                return True
        except Exception as e:
            logger.warning(f"CoinGecko validation failed for cleaned token {clean_token}: {e}")
        
        if chain_id:
            try:
                moralis_valid = await _validate_with_moralis(clean_token, chain_id)
                if moralis_valid:
                    logger.info(f"Cleaned token {clean_token} validated by Moralis")
                    _add_to_cache(token_id, chain_id, True)
                    return True
            except Exception as e:
                logger.warning(f"Moralis validation failed for cleaned token {clean_token}: {e}")
            
            # Try QuickNode with cleaned token
            if QUICKNODE_API_KEY and QUICKNODE_ENDPOINT:
                try:
                    quicknode_valid = await _validate_with_quicknode(clean_token, chain_id)
                    if quicknode_valid:
                        logger.info(f"Cleaned token {clean_token} validated by QuickNode")
                        _add_to_cache(token_id, chain_id, True)
                        return True
                except Exception as e:
                    logger.warning(f"QuickNode validation failed for cleaned token {clean_token}: {e}")
    
    # For tokens with $ prefix, we'll be more permissive
    # This allows users to swap new or less common tokens
    if token_id.startswith('$'):
        clean_token = token_id[1:]
        logger.info(f"Permissively allowing $ prefixed token: {token_id} -> {clean_token}")
        
        # Add a warning in the logs but allow the token
        logger.warning(
            f"CAUTION: Allowing unverified token with $ prefix: {token_id}. "
            f"This token has not been validated through standard methods. "
            f"Users should verify the contract address before swapping."
        )
        
        _add_to_cache(token_id, chain_id, True)
        return True
    
    # Be more permissive with any token that looks like a valid token symbol
    # This is a heuristic approach - we'll allow tokens that follow typical naming patterns
    if re.match(r'^[A-Za-z0-9]{2,10}$', token_id):
        logger.info(f"Permissively allowing token with valid symbol pattern: {token_id}")
        logger.warning(
            f"CAUTION: Allowing unverified token with valid symbol pattern: {token_id}. "
            f"This token has not been validated through standard methods. "
            f"Users should verify the contract address before swapping."
        )
        _add_to_cache(token_id, chain_id, True)
        return True
    
    # If we reach here, token is not valid by our standards
    # But we'll log a warning rather than completely blocking it
    logger.warning(
        f"Token {token_id} could not be validated through standard methods. "
        f"This token will be rejected for safety reasons. "
        f"If this is a legitimate token, consider using its contract address directly."
    )
    _add_to_cache(token_id, chain_id, False)
    return False

async def _validate_with_coingecko(token_id: str) -> bool:
    """Validate token using CoinGecko's search API."""
    variations = [
        token_id,
        token_id.lower(),
        token_id.upper(),
        token_id.capitalize()
    ]
    
    for variation in variations:
        try:
            url = f"https://api.coingecko.com/api/v3/search"
            params = {"query": variation}
            
            async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={"x-cg-demo-api-key": os.environ["COINGECKO_API_KEY"]},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    coins = data.get("coins", [])
                    
                    # Check both symbol and name matches
                    normalized_query = _normalize_token(variation)
                    for coin in coins:
                        if (normalized_query == _normalize_token(coin["symbol"]) or
                            normalized_query == _normalize_token(coin["name"])):
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
        url = f"https://deep-index.moralis.io/api/v2.2/erc20/metadata/symbols"
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
            search_url = f"https://deep-index.moralis.io/api/v2.2/erc20/tokens"
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

async def _validate_with_quicknode(token_id: str, chain_id: int) -> bool:
    """Validate token using QuickNode's API."""
    if not QUICKNODE_API_KEY or not QUICKNODE_ENDPOINT:
        logger.warning("QuickNode API key or endpoint not configured")
        return False
        
    try:
        # First try to search by symbol
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "qn_searchTokens",
            "params": {
                "query": token_id,
                "chainId": str(chain_id),
                "limit": 10
            }
        }
        
        async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
            response = await client.post(
                QUICKNODE_ENDPOINT,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data and data["result"] and len(data["result"]) > 0:
                    # Check if any of the results match our token
                    normalized_token = _normalize_token(token_id)
                    for token in data["result"]:
                        if (_normalize_token(token.get("symbol", "")) == normalized_token or
                            _normalize_token(token.get("name", "")) == normalized_token):
                            return True
                            
        # If symbol search fails, try to get token metadata by name
        # This is a more permissive approach
        variations = [
            token_id,
            token_id.lower(),
            token_id.upper(),
            token_id.capitalize()
        ]
        
        for variation in variations:
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "qn_getTokenMetadataByName",
                "params": {
                    "name": variation,
                    "chainId": str(chain_id)
                }
            }
            
            async with httpx.AsyncClient(verify=not DISABLE_SSL_VERIFY) as client:
                response = await client.post(
                    QUICKNODE_ENDPOINT,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data and data["result"] and len(data["result"]) > 0:
                        return True
                        
    except Exception as e:
        logger.warning(f"QuickNode validation failed: {e}")
        
    return False 