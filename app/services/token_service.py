import os
import logging
import aiohttp
import ssl
from typing import Dict, Optional, Tuple, List
from app.config.chains import TOKEN_ADDRESSES
from eth_utils import is_address, to_checksum_address

logger = logging.getLogger(__name__)

# Token aliases mapping
TOKEN_ALIASES = {
    # Common aliases
    "ETH": ["WETH", "ETHEREUM"],
    "USDC": ["USD", "USDC.E"],
    "USDT": ["TETHER"],
    "BTC": ["WBTC", "BITCOIN"],
    
    # Chain-specific tokens
    "SCR": ["$SCR", "SCROLL"],  # Scroll token
    "OP": ["$OP", "OPTIMISM"],  # Optimism token
    "ARB": ["$ARB", "ARBITRUM"],  # Arbitrum token
    "BASE": ["$BASE"],  # Base token
    "MATIC": ["$MATIC", "POLYGON"],  # Polygon token
}

# Reverse lookup for aliases
REVERSE_ALIASES = {}
for main_token, aliases in TOKEN_ALIASES.items():
    for alias in aliases:
        REVERSE_ALIASES[alias] = main_token

# Cache for contract address to token symbol mappings
# Structure: {(contract_address, chain_id): (symbol, name)}
CONTRACT_CACHE = {}

class TokenService:
    """Service for token-related operations."""
    
    def __init__(self):
        self.moralis_api_key = os.environ.get("MORALIS_API_KEY")
        self.coingecko_api_key = os.environ.get("COINGECKO_API_KEY")
        
        # Determine if we should verify SSL certificates
        # In development, we might want to disable this if there are certificate issues
        self.verify_ssl = os.environ.get("DISABLE_SSL_VERIFY", "").lower() != "true"
        if not self.verify_ssl:
            logger.warning("SSL certificate verification is disabled. This should only be used in development.")
        
        # Chain ID to Moralis chain name mapping
        self.chain_mapping = {
            1: "eth",
            10: "optimism",
            56: "bsc",
            137: "polygon",
            42161: "arbitrum",
            8453: "base",
            534352: "scroll"
        }
    
    async def lookup_token(self, token_symbol: str, chain_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Look up a token by symbol or alias and return its address, canonical symbol, and name.
        
        Args:
            token_symbol: The token symbol, alias, or contract address to look up
            chain_id: The chain ID to look up the token on
            
        Returns:
            Tuple of (token_address, canonical_symbol, token_name) or (None, None, None) if not found
        """
        # Check if it's a contract address first
        if is_address(token_symbol):
            checksum_address = to_checksum_address(token_symbol)
            logger.info(f"Token {token_symbol} is a valid contract address: {checksum_address}")
            
            # Check if we have this contract address in our cache
            if (checksum_address, chain_id) in CONTRACT_CACHE:
                symbol, name = CONTRACT_CACHE[(checksum_address, chain_id)]
                logger.info(f"Found cached contract info: {checksum_address} -> {symbol} ({name})")
                return checksum_address, symbol, name
            
            # Look up the token metadata to get the symbol
            metadata = await self._get_token_metadata_by_address(checksum_address, chain_id)
            if metadata:
                symbol = metadata.get("symbol", "").upper()
                name = metadata.get("name", "Unknown Token")
                # Cache the result
                CONTRACT_CACHE[(checksum_address, chain_id)] = (symbol, name)
                logger.info(f"Found token metadata for {checksum_address}: {symbol} ({name})")
                return checksum_address, symbol, name
            
            # If we couldn't get metadata, just return the address
            return checksum_address, None, None
        
        # Clean up the token symbol
        clean_symbol = token_symbol.upper().strip()
        original_symbol = clean_symbol  # Keep original for logging
        
        # Handle $ prefix and other special characters
        if clean_symbol.startswith("$"):
            clean_symbol = clean_symbol[1:]  # Remove $ prefix
        
        logger.info(f"Looking up token: {original_symbol} (cleaned to {clean_symbol}) on chain {chain_id}")
        
        # Check if it's a known alias
        if clean_symbol in REVERSE_ALIASES:
            canonical_symbol = REVERSE_ALIASES[clean_symbol]
            logger.info(f"Found alias {clean_symbol} -> {canonical_symbol}")
            clean_symbol = canonical_symbol
        elif original_symbol in REVERSE_ALIASES:
            canonical_symbol = REVERSE_ALIASES[original_symbol]
            logger.info(f"Found alias for original symbol {original_symbol} -> {canonical_symbol}")
            clean_symbol = canonical_symbol
        
        # Check if it's in our predefined token addresses
        chain_tokens = TOKEN_ADDRESSES.get(chain_id, {})
        if clean_symbol in chain_tokens:
            logger.info(f"Found token {clean_symbol} in predefined addresses")
            return chain_tokens[clean_symbol], clean_symbol, None
        
        # Try Moralis API
        result = await self._lookup_token_moralis(clean_symbol, chain_id)
        if result[0]:
            logger.info(f"Found token {clean_symbol} via Moralis")
            return result
            
        # Try CoinGecko as fallback
        result = await self._lookup_token_coingecko(clean_symbol)
        if result[0]:
            logger.info(f"Found token {clean_symbol} via CoinGecko")
            return result
            
        # If we still haven't found it, try with a more aggressive cleaning
        # Remove all non-alphanumeric characters
        alphanumeric_symbol = ''.join(c for c in original_symbol if c.isalnum()).upper()
        if alphanumeric_symbol != clean_symbol:
            logger.info(f"Trying more aggressive cleaning: {original_symbol} -> {alphanumeric_symbol}")
            
            # Check if it's a known alias after aggressive cleaning
            if alphanumeric_symbol in REVERSE_ALIASES:
                canonical_symbol = REVERSE_ALIASES[alphanumeric_symbol]
                logger.info(f"Found alias after aggressive cleaning {alphanumeric_symbol} -> {canonical_symbol}")
                alphanumeric_symbol = canonical_symbol
            
            # Check predefined addresses again
            if alphanumeric_symbol in chain_tokens:
                logger.info(f"Found token {alphanumeric_symbol} in predefined addresses after aggressive cleaning")
                return chain_tokens[alphanumeric_symbol], alphanumeric_symbol, None
                
            # Try Moralis and CoinGecko again with cleaned symbol
            result = await self._lookup_token_moralis(alphanumeric_symbol, chain_id)
            if result[0]:
                logger.info(f"Found token {alphanumeric_symbol} via Moralis after aggressive cleaning")
                return result
                
            result = await self._lookup_token_coingecko(alphanumeric_symbol)
            if result[0]:
                logger.info(f"Found token {alphanumeric_symbol} via CoinGecko after aggressive cleaning")
                return result
        
        # For tokens with $ prefix that we couldn't find, we'll try to look them up by name
        if original_symbol.startswith('$'):
            # Try to look up by name instead of symbol
            clean_name = clean_symbol  # Use the cleaned symbol as a name search
            logger.info(f"Trying to look up token by name: {clean_name}")
            
            # Try Moralis search by name
            result = await self._search_token_by_name(clean_name, chain_id)
            if result[0]:
                logger.info(f"Found token {clean_name} via name search")
                return result
            
            logger.warning(f"Could not find token {original_symbol}, but allowing it as a special token")
            # Return the clean symbol as both address and symbol
            # The UI should handle this special case and warn the user
            return None, clean_symbol, f"Unverified token: {clean_symbol}"
            
        logger.warning(f"Could not find token {original_symbol} through any method")
        return None, None, None
    
    async def _lookup_token_moralis(self, symbol: str, chain_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using Moralis API."""
        if not self.moralis_api_key:
            logger.warning("Moralis API key not found, skipping token lookup")
            return None, None, None
        
        try:
            moralis_chain = self.chain_mapping.get(chain_id)
            if not moralis_chain:
                logger.warning(f"Chain {chain_id} not supported by Moralis")
                return None, None, None
            
            # Create a custom SSL context if we're not verifying certificates
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                url = f"https://deep-index.moralis.io/api/v2/erc20/metadata/symbols"
                params = {
                    "chain": moralis_chain,
                    "symbols": symbol
                }
                headers = {
                    "accept": "application/json",
                    "X-API-Key": self.moralis_api_key
                }
                
                async with session.get(url, params=params, headers=headers, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            token_data = data[0]
                            logger.info(f"Found token via Moralis: {token_data}")
                            return token_data.get("address"), token_data.get("symbol"), token_data.get("name")
                    else:
                        logger.warning(f"Moralis API returned status {response.status}")
        
        except Exception as e:
            logger.error(f"Error looking up token with Moralis: {e}")
        
        return None, None, None
    
    async def _lookup_token_coingecko(self, symbol: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using CoinGecko API."""
        if not self.coingecko_api_key:
            return None, None, None
                
        try:
            # Create a custom SSL context if we're not verifying certificates
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            async with aiohttp.ClientSession() as session:
                url = "https://pro-api.coingecko.com/api/v3/search"
                params = {
                    "query": symbol,
                    "x_cg_pro_api_key": self.coingecko_api_key
                }
                
                async with session.get(url, params=params, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "coins" in data and len(data["coins"]) > 0:
                            coin = data["coins"][0]
                            logger.info(f"Found token via CoinGecko: {coin}")
                            # CoinGecko doesn't provide contract addresses directly in search
                            # We'd need to make another call to get the contract address
                            return None, coin.get("symbol").upper(), coin.get("name")
        
        except Exception as e:
            logger.error(f"Error looking up token with CoinGecko: {e}")
        
        return None, None, None
    
    async def _search_token_by_name(self, name: str, chain_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Search for a token by name using Moralis API."""
        if not self.moralis_api_key:
            return None, None, None
            
        try:
            moralis_chain = self.chain_mapping.get(chain_id)
            if not moralis_chain:
                return None, None, None
            
            # Create a custom SSL context if we're not verifying certificates
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            async with aiohttp.ClientSession() as session:
                url = f"https://deep-index.moralis.io/api/v2/erc20/metadata/search"
                params = {
                    "chain": moralis_chain,
                    "q": name
                }
                headers = {
                    "accept": "application/json",
                    "X-API-Key": self.moralis_api_key
                }
                
                async with session.get(url, params=params, headers=headers, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            # Find the best match
                            best_match = None
                            for token in data:
                                token_name = token.get("name", "").upper()
                                token_symbol = token.get("symbol", "").upper()
                                
                                # Check for exact matches first
                                if name.upper() == token_name or name.upper() == token_symbol:
                                    best_match = token
                                    break
                                    
                                # Then check for partial matches
                                if name.upper() in token_name or name.upper() in token_symbol:
                                    best_match = token
                                    
                            if best_match:
                                logger.info(f"Found token via name search: {best_match}")
                                return best_match.get("address"), best_match.get("symbol"), best_match.get("name")
        
        except Exception as e:
            logger.error(f"Error searching token by name: {e}")
            
        return None, None, None
    
    async def _get_token_metadata_by_address(self, address: str, chain_id: int) -> Optional[Dict]:
        """Get token metadata by contract address."""
        if not self.moralis_api_key:
            return None
            
        try:
            moralis_chain = self.chain_mapping.get(chain_id)
            if not moralis_chain:
                return None
            
            # Create a custom SSL context if we're not verifying certificates
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            async with aiohttp.ClientSession() as session:
                url = f"https://deep-index.moralis.io/api/v2/erc20/metadata"
                params = {
                    "chain": moralis_chain,
                    "addresses": address
                }
                headers = {
                    "accept": "application/json",
                    "X-API-Key": self.moralis_api_key
                }
                
                async with session.get(url, params=params, headers=headers, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            return data[0]
        
        except Exception as e:
            logger.error(f"Error getting token metadata by address: {e}")
            
        return None 