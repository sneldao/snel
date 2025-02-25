import os
import logging
import aiohttp
import ssl
import json
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
    "NURI": ["$NURI"],  # NURI token
}

# Reverse lookup for aliases
REVERSE_ALIASES = {}
for main_token, aliases in TOKEN_ALIASES.items():
    for alias in aliases:
        REVERSE_ALIASES[alias] = main_token

# Cache for contract address to token symbol mappings
# Structure: {(contract_address, chain_id): (symbol, name)}
CONTRACT_CACHE = {}

# Known token addresses cache - populated from TOKEN_ADDRESSES on init
KNOWN_TOKEN_ADDRESSES = {}

class TokenService:
    """Service for token-related operations."""
    
    def __init__(self):
        self.moralis_api_key = os.environ.get("MORALIS_API_KEY")
        self.coingecko_api_key = os.environ.get("COINGECKO_API_KEY")
        self.quicknode_api_key = os.environ.get("QUICKNODE_API_KEY")
        
        # Determine if we should verify SSL certificates
        # In development, we might want to disable this if there are certificate issues
        self.verify_ssl = os.environ.get("DISABLE_SSL_VERIFY", "").lower() != "true"
        if not self.verify_ssl:
            logger.warning("SSL certificate verification is disabled. This should only be used in development.")
        
        # Path to custom CA certificates bundle (for production)
        self.ca_cert_path = os.environ.get("CA_CERT_PATH")
        
        # Check if we're running in a Vercel environment
        self.is_vercel = os.environ.get("VERCEL", "").lower() == "1"
        
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
        
        # Chain ID to QuickNode endpoint mapping
        self.quicknode_endpoints = {}
        
        # If QuickNode API key is provided, construct endpoints for all supported chains
        if self.quicknode_api_key:
            # Base URL pattern for QuickNode endpoints
            base_url_pattern = "https://frequent-withered-surf.{network}.quiknode.pro/{api_key}/"
            avalanche_url_pattern = "https://frequent-withered-surf.avalanche-mainnet.quiknode.pro/{api_key}/ext/bc/C/rpc/"
            
            # Network identifiers for each chain
            network_mapping = {
                1: "eth-mainnet",
                10: "optimism",
                137: "matic",
                42161: "arbitrum-mainnet",
                8453: "base-mainnet",
                534352: "scroll-mainnet",
                43114: "avalanche-mainnet"  # Special case for Avalanche
            }
            
            # Construct endpoints for each supported chain
            for chain_id, network in network_mapping.items():
                # Use environment variable if provided, otherwise construct from API key
                env_var_name = f"QUICKNODE_{network.upper().replace('-', '_')}_URL"
                env_url = os.environ.get(env_var_name)
                
                if env_url:
                    self.quicknode_endpoints[chain_id] = env_url
                elif chain_id == 43114:  # Avalanche has a different URL pattern
                    self.quicknode_endpoints[chain_id] = avalanche_url_pattern.format(api_key=self.quicknode_api_key)
                else:
                    self.quicknode_endpoints[chain_id] = base_url_pattern.format(network=network, api_key=self.quicknode_api_key)
            
            logger.info(f"Configured QuickNode endpoints for chains: {list(self.quicknode_endpoints.keys())}")
        else:
            logger.warning("QuickNode API key not provided, QuickNode token lookup will be disabled")
        
        # Populate known token addresses from config
        self._populate_known_tokens()
    
    def _populate_known_tokens(self):
        """Populate known token addresses from TOKEN_ADDRESSES config."""
        global KNOWN_TOKEN_ADDRESSES
        
        # Create a mapping of token symbols to addresses for each chain
        for chain_id, tokens in TOKEN_ADDRESSES.items():
            for symbol, address in tokens.items():
                if symbol not in KNOWN_TOKEN_ADDRESSES:
                    KNOWN_TOKEN_ADDRESSES[symbol] = {}
                KNOWN_TOKEN_ADDRESSES[symbol][chain_id] = address
                
                # Also add lowercase version
                symbol_lower = symbol.lower()
                if symbol_lower not in KNOWN_TOKEN_ADDRESSES:
                    KNOWN_TOKEN_ADDRESSES[symbol_lower] = {}
                KNOWN_TOKEN_ADDRESSES[symbol_lower][chain_id] = address
                
        logger.info(f"Populated known token addresses: {KNOWN_TOKEN_ADDRESSES}")
    
    def _create_ssl_context(self):
        """Create an SSL context based on configuration."""
        if not self.verify_ssl:
            # Disable SSL verification (for development only)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        elif hasattr(self, 'ca_cert_path') and self.ca_cert_path:
            # Use custom CA certificates (for production)
            ssl_context = ssl.create_default_context(cafile=self.ca_cert_path)
            return ssl_context
        elif self.is_vercel:
            # In Vercel, we rely on the platform's CA certificates
            # No need to create a custom context
            return None
        else:
            # Use default SSL context
            return None
    
    async def lookup_token(self, token_symbol: str, chain_id: int) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[Dict]]:
        """
        Look up a token by symbol or alias and return its address, canonical symbol, name, and additional metadata.
        
        Args:
            token_symbol: The token symbol, alias, or contract address to look up
            chain_id: The chain ID to look up the token on
            
        Returns:
            Tuple of (token_address, canonical_symbol, token_name, metadata) or (None, None, None, None) if not found
            metadata is a dictionary containing additional information about the token:
            {
                "verified": bool,  # Whether the token is verified
                "source": str,     # Where the token info was found (e.g., "predefined", "moralis", "quicknode", "coingecko")
                "decimals": int,   # Token decimals if available
                "logo_url": str,   # URL to token logo if available
                "description": str, # Token description if available
                "warning": str,    # Warning message if any
            }
        """
        # Check if it's a contract address first
        if is_address(token_symbol):
            checksum_address = to_checksum_address(token_symbol)
            logger.info(f"Token {token_symbol} is a valid contract address: {checksum_address}")
            
            # Check if we have this contract address in our cache
            if (checksum_address, chain_id) in CONTRACT_CACHE:
                symbol, name = CONTRACT_CACHE[(checksum_address, chain_id)]
                logger.info(f"Found cached contract info: {checksum_address} -> {symbol} ({name})")
                return checksum_address, symbol, name, {"verified": True, "source": "cache"}
            
            # Look up the token metadata to get the symbol
            metadata = await self._get_token_metadata_by_address(checksum_address, chain_id)
            if metadata:
                symbol = metadata.get("symbol", "").upper()
                name = metadata.get("name", "Unknown Token")
                decimals = metadata.get("decimals")
                # Cache the result
                CONTRACT_CACHE[(checksum_address, chain_id)] = (symbol, name)
                logger.info(f"Found token metadata for {checksum_address}: {symbol} ({name})")
                
                # Create metadata dictionary
                token_metadata = {
                    "verified": True,
                    "source": "api",
                    "decimals": decimals,
                    "logo_url": None,
                    "description": None,
                    "warning": None
                }
                
                return checksum_address, symbol, name, token_metadata
            
            # If we couldn't get metadata, just return the address with a warning
            return checksum_address, None, None, {
                "verified": False,
                "source": "address_only",
                "warning": "This token address could not be verified. Please ensure it is the correct contract address."
            }
        
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
            return chain_tokens[clean_symbol], clean_symbol, None, {
                "verified": True,
                "source": "predefined",
                "decimals": TOKEN_DECIMALS.get(clean_symbol, 18),
                "warning": None
            }
        
        # Check if it's in our known token addresses
        if clean_symbol in KNOWN_TOKEN_ADDRESSES and chain_id in KNOWN_TOKEN_ADDRESSES[clean_symbol]:
            address = KNOWN_TOKEN_ADDRESSES[clean_symbol][chain_id]
            logger.info(f"Found token {clean_symbol} in known token addresses: {address}")
            return address, clean_symbol, None, {
                "verified": True,
                "source": "known_addresses",
                "decimals": TOKEN_DECIMALS.get(clean_symbol, 18),
                "warning": None
            }
        
        # Try Moralis API
        result = await self._lookup_token_moralis(clean_symbol, chain_id)
        if result[0]:
            logger.info(f"Found token {clean_symbol} via Moralis")
            address, symbol, name = result
            return address, symbol, name, {
                "verified": True,
                "source": "moralis",
                "decimals": None,  # We don't get decimals from this API call
                "warning": None
            }
        
        # Try QuickNode API
        result = await self._lookup_token_quicknode(clean_symbol, chain_id)
        if result[0]:
            logger.info(f"Found token {clean_symbol} via QuickNode")
            address, symbol, name = result
            return address, symbol, name, {
                "verified": True,
                "source": "quicknode",
                "decimals": None,  # We don't get decimals from this API call
                "warning": None
            }
            
        # Try CoinGecko as fallback
        result = await self._lookup_token_coingecko(clean_symbol)
        if result[0]:
            logger.info(f"Found token {clean_symbol} via CoinGecko")
            address, symbol, name = result
            return address, symbol, name, {
                "verified": True,
                "source": "coingecko",
                "decimals": None,
                "warning": None
            }
            
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
                return chain_tokens[alphanumeric_symbol], alphanumeric_symbol, None, {
                    "verified": True,
                    "source": "predefined",
                    "decimals": TOKEN_DECIMALS.get(alphanumeric_symbol, 18),
                    "warning": None
                }
                
            # Try Moralis, QuickNode, and CoinGecko again with cleaned symbol
            result = await self._lookup_token_moralis(alphanumeric_symbol, chain_id)
            if result[0]:
                logger.info(f"Found token {alphanumeric_symbol} via Moralis after aggressive cleaning")
                address, symbol, name = result
                return address, symbol, name, {
                    "verified": True,
                    "source": "moralis",
                    "decimals": None,
                    "warning": None
                }
            
            result = await self._lookup_token_quicknode(alphanumeric_symbol, chain_id)
            if result[0]:
                logger.info(f"Found token {alphanumeric_symbol} via QuickNode after aggressive cleaning")
                address, symbol, name = result
                return address, symbol, name, {
                    "verified": True,
                    "source": "quicknode",
                    "decimals": None,
                    "warning": None
                }
                
            result = await self._lookup_token_coingecko(alphanumeric_symbol)
            if result[0]:
                logger.info(f"Found token {alphanumeric_symbol} via CoinGecko after aggressive cleaning")
                address, symbol, name = result
                return address, symbol, name, {
                    "verified": True,
                    "source": "coingecko",
                    "decimals": None,
                    "warning": None
                }
        
        # For tokens with $ prefix that we couldn't find, we'll try to look them up by name
        if original_symbol.startswith('$'):
            # Try to look up by name instead of symbol
            clean_name = clean_symbol  # Use the cleaned symbol as a name search
            logger.info(f"Trying to look up token by name: {clean_name}")
            
            # Try Moralis search by name
            result = await self._search_token_by_name(clean_name, chain_id)
            if result[0]:
                logger.info(f"Found token {clean_name} via name search")
                address, symbol, name = result
                return address, symbol, name, {
                    "verified": True,
                    "source": "moralis_name_search",
                    "decimals": None,
                    "warning": None
                }
            
            # Special case for NURI token on Scroll
            if clean_symbol == "NURI" and chain_id == 534352:
                nuri_address = "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc"
                logger.info(f"Using hardcoded address for NURI token on Scroll: {nuri_address}")
                return nuri_address, "NURI", "NURI Token", {
                    "verified": True,
                    "source": "hardcoded",
                    "decimals": 18,
                    "warning": None
                }
            
            logger.warning(f"Could not find token {original_symbol}, but allowing it as a special token")
            # Return the clean symbol as both address and symbol with a warning
            return None, clean_symbol, f"Unverified token: {clean_symbol}", {
                "verified": False,
                "source": "unverified",
                "warning": f"The token '{original_symbol}' could not be verified. If you want to proceed, you'll need to provide the contract address."
            }
            
        logger.warning(f"Could not find token {original_symbol} through any method")
        return None, None, None, {
            "verified": False,
            "source": "not_found",
            "warning": f"The token '{original_symbol}' could not be found. Please check the spelling or provide the contract address."
        }
    
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
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
            
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
    
    async def _lookup_token_quicknode(self, symbol: str, chain_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using QuickNode API."""
        if not self.quicknode_api_key:
            logger.warning("QuickNode API key not found, skipping token lookup")
            return None, None, None
        
        try:
            endpoint = self.quicknode_endpoints.get(chain_id)
            if not endpoint:
                logger.warning(f"Chain {chain_id} not supported by QuickNode")
                return None, None, None
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
            # Create a custom SSL context if we're not verifying certificates
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # For QuickNode, we'll use a different approach
            # We'll use the eth_call method to call the ERC20 token registry contract
            # This is a more reliable way to get token information
            
            # First, let's try to find the token in popular token lists
            # We'll use a simplified approach for now - just check for common tokens
            common_tokens = {
                "ETH": {
                    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH on Ethereum
                    10: "0x4200000000000000000000000000000000000006",  # WETH on Optimism
                    137: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH on Polygon
                    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH on Arbitrum
                    8453: "0x4200000000000000000000000000000000000006",  # WETH on Base
                    534352: "0x5300000000000000000000000000000000000004",  # WETH on Scroll
                },
                "USDC": {
                    1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC on Ethereum
                    10: "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",  # USDC on Optimism
                    137: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC on Polygon
                    42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # USDC on Arbitrum
                    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
                    534352: "0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4",  # USDC on Scroll
                },
                "USDT": {
                    1: "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT on Ethereum
                    10: "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",  # USDT on Optimism
                    137: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",  # USDT on Polygon
                    42161: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",  # USDT on Arbitrum
                    8453: "0x4A3A6Dd60A34bB2Aba60D73B4C88315E9CeB6A3D",  # USDT on Base
                },
                "OP": {
                    10: "0x4200000000000000000000000000000000000042",  # OP on Optimism
                },
                "ARB": {
                    42161: "0x912CE59144191C1204E64559FE8253a0e49E6548",  # ARB on Arbitrum
                },
                "MATIC": {
                    137: "0x0000000000000000000000000000000000001010",  # MATIC on Polygon
                },
                "SCR": {
                    534352: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # SCR on Scroll
                },
                "NURI": {
                    534352: "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc",  # NURI on Scroll
                }
            }
            
            # Check if the token is in our common tokens list
            upper_symbol = symbol.upper()
            if upper_symbol in common_tokens and chain_id in common_tokens[upper_symbol]:
                address = common_tokens[upper_symbol][chain_id]
                
                # Get token metadata
                metadata = await self._get_token_metadata_by_address_quicknode(address, chain_id)
                if metadata:
                    logger.info(f"Found token {upper_symbol} in common tokens list: {address}")
                    return address, metadata.get("symbol"), metadata.get("name")
                else:
                    # If we can't get metadata, just return the address and symbol
                    logger.info(f"Found token {upper_symbol} in common tokens list but couldn't get metadata: {address}")
                    return address, upper_symbol, None
            
            # If we couldn't find the token in our common tokens list, we'll try to search for it
            # This is a more complex operation and might not be supported by all QuickNode endpoints
            # For now, we'll just return None
            logger.warning(f"Token {symbol} not found in common tokens list for chain {chain_id}")
            return None, None, None
            
        except Exception as e:
            logger.error(f"Error looking up token with QuickNode: {e}")
        
        return None, None, None
    
    async def _lookup_token_coingecko(self, symbol: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using CoinGecko API."""
        if not self.coingecko_api_key:
            return None, None, None
                
        try:
            # Create SSL context
            ssl_context = self._create_ssl_context()
                
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
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
            
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
        # Try Moralis first
        metadata = await self._get_token_metadata_by_address_moralis(address, chain_id)
        if metadata:
            return metadata
            
        # Try QuickNode if Moralis fails
        metadata = await self._get_token_metadata_by_address_quicknode(address, chain_id)
        if metadata:
            return metadata
            
        return None
    
    async def _get_token_metadata_by_address_moralis(self, address: str, chain_id: int) -> Optional[Dict]:
        """Get token metadata by contract address using Moralis."""
        if not self.moralis_api_key:
            return None
            
        try:
            moralis_chain = self.chain_mapping.get(chain_id)
            if not moralis_chain:
                return None
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
                
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
            logger.error(f"Error getting token metadata by address with Moralis: {e}")
            
        return None
    
    async def _get_token_metadata_by_address_quicknode(self, address: str, chain_id: int) -> Optional[Dict]:
        """Get token metadata by contract address using QuickNode."""
        if not self.quicknode_api_key:
            return None
            
        try:
            endpoint = self.quicknode_endpoints.get(chain_id)
            if not endpoint:
                return None
            
            # Create SSL context
            ssl_context = self._create_ssl_context()
                
            async with aiohttp.ClientSession() as session:
                # Use standard JSON-RPC calls to get token metadata
                # First, get the token symbol
                symbol_payload = {
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [
                        {
                            "to": address,
                            "data": "0x95d89b41"  # keccak256("symbol()")
                        },
                        "latest"
                    ]
                }
                
                # Then, get the token name
                name_payload = {
                    "id": 2,
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [
                        {
                            "to": address,
                            "data": "0x06fdde03"  # keccak256("name()")
                        },
                        "latest"
                    ]
                }
                
                # Finally, get the token decimals
                decimals_payload = {
                    "id": 3,
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [
                        {
                            "to": address,
                            "data": "0x313ce567"  # keccak256("decimals()")
                        },
                        "latest"
                    ]
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                # Make the requests
                symbol_response = None
                name_response = None
                decimals_response = None
                
                try:
                    async with session.post(endpoint, json=symbol_payload, headers=headers, ssl=ssl_context) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data:
                                symbol_response = data["result"]
                except Exception as e:
                    logger.error(f"Error getting token symbol: {e}")
                
                try:
                    async with session.post(endpoint, json=name_payload, headers=headers, ssl=ssl_context) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data:
                                name_response = data["result"]
                except Exception as e:
                    logger.error(f"Error getting token name: {e}")
                
                try:
                    async with session.post(endpoint, json=decimals_payload, headers=headers, ssl=ssl_context) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data:
                                decimals_response = data["result"]
                except Exception as e:
                    logger.error(f"Error getting token decimals: {e}")
                
                # Parse the responses
                symbol = None
                name = None
                decimals = None
                
                if symbol_response and symbol_response.startswith("0x"):
                    try:
                        # Remove 0x prefix and convert hex to bytes
                        hex_data = symbol_response[2:]
                        # The first 32 bytes (64 chars) are the offset, the next 32 bytes are the length
                        # The actual string data starts after that
                        length = int(hex_data[64:128], 16)
                        string_data = hex_data[128:128+length*2]
                        symbol = bytes.fromhex(string_data).decode('utf-8')
                    except Exception as e:
                        logger.error(f"Error parsing token symbol: {e}")
                
                if name_response and name_response.startswith("0x"):
                    try:
                        # Remove 0x prefix and convert hex to bytes
                        hex_data = name_response[2:]
                        # The first 32 bytes (64 chars) are the offset, the next 32 bytes are the length
                        # The actual string data starts after that
                        length = int(hex_data[64:128], 16)
                        string_data = hex_data[128:128+length*2]
                        name = bytes.fromhex(string_data).decode('utf-8')
                    except Exception as e:
                        logger.error(f"Error parsing token name: {e}")
                
                if decimals_response and decimals_response.startswith("0x"):
                    try:
                        # Remove 0x prefix and convert hex to int
                        decimals = int(decimals_response[2:], 16)
                    except Exception as e:
                        logger.error(f"Error parsing token decimals: {e}")
                
                if symbol or name:
                    logger.info(f"Found token metadata via QuickNode: symbol={symbol}, name={name}, decimals={decimals}")
                    return {
                        "address": address,
                        "symbol": symbol,
                        "name": name,
                        "decimals": decimals
                    }
        
        except Exception as e:
            logger.error(f"Error getting token metadata by address with QuickNode: {e}")
            
        return None 