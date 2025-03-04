import os
import logging
import aiohttp
import ssl
import json
from typing import Dict, Optional, Tuple, List, Any, Union
from app.config.chains import TOKEN_ADDRESSES, TOKEN_DECIMALS
from eth_utils import is_address, to_checksum_address
import httpx

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
CONTRACT_CACHE: Dict[Tuple[str, int], Tuple[str, str]] = {}

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
        if not self.verify_ssl and not os.environ.get("SSL_WARNING_SHOWN"):
            logger.warning("⚠️ SECURITY WARNING: SSL certificate verification is disabled. This makes your connections less secure and should ONLY be used during development.")
            # Mark that we've shown the warning
            os.environ["SSL_WARNING_SHOWN"] = "true"
        
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
    
    async def lookup_token(
        self, 
        token_symbol: Union[str, Dict],
        chain_id: int
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[Dict]]:
        """
        Look up a token by symbol, address, or token info dictionary.
        
        Args:
            token_symbol: The token symbol, address, or token info dictionary
            chain_id: The blockchain ID
            
        Returns:
            Tuple containing (address, symbol, name, metadata) or (None, None, None, None) if not found
        """
        # If we received a dictionary, extract the necessary information
        if isinstance(token_symbol, dict):
            address = token_symbol.get("address")
            symbol = token_symbol.get("symbol")
            name = token_symbol.get("name")
            
            if address and is_address(address):
                logger.info(f"Using provided token info: {symbol} ({name}) at {address}")
                links = self._get_verification_links(address, chain_id)
                return address, symbol, name, {
                    "verified": True,
                    "source": "provided",
                    "links": links
                }
        
        # If it's a string, proceed with normal lookup
        original_input = token_symbol if isinstance(token_symbol, str) else str(token_symbol)
        clean_symbol = original_input.lstrip('$').upper()  # Remove $ prefix for lookups
        
        logger.info(f"Looking up token: {original_input} (cleaned to {clean_symbol}) on chain {chain_id}")

        # Check if it's a contract address
        if is_address(original_input):
            return await self._lookup_token_by_address(original_input, chain_id)
        
        # For standard tokens, try predefined addresses first
        if clean_symbol in TOKEN_ADDRESSES.get(chain_id, {}):
            address = TOKEN_ADDRESSES[chain_id][clean_symbol]
            logger.info(f"Found predefined token: {clean_symbol} -> {address}")
            links = self._get_verification_links(address, chain_id)
            return address, clean_symbol, clean_symbol, {
                "verified": True, 
                "source": "predefined",
                "links": links,
                "is_custom": False
            }
        
        # For custom tokens (starting with $), try external APIs first
        if original_input.startswith('$'):
            logger.info(f"Looking up custom token via external APIs first: {clean_symbol}")
            result = await self._try_external_apis(clean_symbol, chain_id, original_input)
            if result[0]:
                return result
            
            # Not found in any source, return custom token info with guidance
            chain_name = self._get_chain_name(chain_id)
            return None, original_input, original_input, {
                "verified": False,
                "source": "custom",
                "is_custom": True,
                "warning": f"Custom token - please provide the contract address for {original_input} on {chain_name}",
                "required_info": {
                    "contract_address": True,
                    "chain_id": chain_id,
                    "chain_name": chain_name
                },
                "links": {}  # Empty links but still include the field
            }
        
        # If not found in predefined list, try external APIs
        result = await self._try_external_apis(clean_symbol, chain_id, original_input)
        if result[0]:
            return result
        
        # Not found anywhere
        logger.warning(f"Token not found: {original_input}")
        return None, None, None, None
    
    def _get_verification_links(self, address: str, chain_id: int, coin_id: Optional[str] = None) -> Dict[str, str]:
        """Generate verification links for a token."""
        links = {}
        
        # Block explorer links based on chain
        explorer_urls = {
            1: f"https://etherscan.io/token/{address}",
            10: f"https://optimistic.etherscan.io/token/{address}",
            137: f"https://polygonscan.com/token/{address}",
            42161: f"https://arbiscan.io/token/{address}",
            8453: f"https://basescan.org/token/{address}",
            534352: f"https://scrollscan.com/token/{address}"
        }
        
        if chain_id in explorer_urls:
            links["explorer"] = explorer_urls[chain_id]
        
        # DexScreener link
        dex_chain_names = {
            1: "ethereum",
            10: "optimism",
            137: "polygon",
            42161: "arbitrum",
            8453: "base",
            534352: "scroll"
        }
        if chain_id in dex_chain_names:
            links["dexscreener"] = f"https://dexscreener.com/{dex_chain_names[chain_id]}/{address}"
        
        # CoinGecko link if we have the coin_id
        if coin_id:
            links["coingecko"] = f"https://www.coingecko.com/en/coins/{coin_id}"
        
        return links

    async def _lookup_token_by_address(
        self, 
        address: str, 
        chain_id: int
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[Dict]]:
        """Look up token by contract address."""
        checksum_address = to_checksum_address(address)
        logger.info(f"Token {address} is a valid contract address: {checksum_address}")
        
        # Check contract cache
        if (checksum_address, chain_id) in CONTRACT_CACHE:
            symbol, name = CONTRACT_CACHE[(checksum_address, chain_id)]
            logger.info(f"Found cached contract info: {checksum_address} -> {symbol} ({name})")
            metadata = {
                "verified": True,
                "source": "cache",
                "links": self._get_verification_links(checksum_address, chain_id)
            }
            return checksum_address, symbol, name, metadata
        
        # Look up metadata
        metadata = await self._get_token_metadata_by_address(checksum_address, chain_id)
        if metadata:
            links = self._get_verification_links(checksum_address, chain_id, metadata.get("coin_id"))
            return checksum_address, metadata.get("symbol"), metadata.get("name"), {
                "verified": True,
                "source": "api",
                "decimals": metadata.get("decimals", 18),
                "links": links
            }
        
        return checksum_address, None, None, {
            "verified": False,
            "source": "address_only",
            "warning": "Unverified token address",
            "links": self._get_verification_links(checksum_address, chain_id)
        }
    
    async def _try_external_apis(
        self, 
        clean_symbol: str, 
        chain_id: int, 
        original_input: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[Dict]]:
        """Try looking up the token in various external APIs."""
        # Try OpenOcean first for all tokens
        result = await self._lookup_token_by_symbol_openocean(clean_symbol, chain_id)
        if result[0]:
            logger.info(f"Found token via OpenOcean: {result}")
            symbol = original_input if original_input.startswith('$') else result[1]
            links = self._get_verification_links(result[0], chain_id)
            return result[0], symbol, result[2], {
                "verified": True, 
                "source": "openocean", 
                "links": links,
                "is_custom": False
            }

        # Try Moralis
        result = await self._lookup_token_moralis(clean_symbol, chain_id)
        if result[0]:
            logger.info(f"Found token via Moralis: {result}")
            symbol = original_input if original_input.startswith('$') else result[1]
            links = self._get_verification_links(result[0], chain_id)
            return result[0], symbol, result[2], {
                "verified": True, 
                "source": "moralis", 
                "links": links,
                "is_custom": False
            }
        
        # Try CoinGecko
        result = await self._lookup_token_coingecko(clean_symbol)
        if result[0]:
            logger.info(f"Found token via CoinGecko: {result}")
            symbol = original_input if original_input.startswith('$') else result[1]
            links = self._get_verification_links(result[0], chain_id, clean_symbol.lower())
            return result[0], symbol, result[2], {
                "verified": True, 
                "source": "coingecko", 
                "links": links,
                "is_custom": False
            }
        
        # Try QuickNode
        result = await self._lookup_token_quicknode(clean_symbol, chain_id)
        if result[0]:
            logger.info(f"Found token via QuickNode: {result}")
            symbol = original_input if original_input.startswith('$') else result[1]
            links = self._get_verification_links(result[0], chain_id)
            return result[0], symbol, result[2], {
                "verified": True, 
                "source": "quicknode", 
                "links": links,
                "is_custom": False
            }
        
        return None, None, None, None
    
    async def _lookup_token_moralis(
        self, 
        token_symbol: str, 
        chain_id: int
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using Moralis API."""
        if not self.moralis_api_key:
            logger.warning("Moralis API key not set")
            return None, None, None

        try:
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

            # Prepare API URL - use the correct v2.2 endpoint for token search
            search_term = token_symbol.lower()
            url = "https://deep-index.moralis.io/api/v2.2/token/search"
            params = {
                "chain": chain,
                "q": search_term,
                "limit": 10
            }

            # Prepare headers
            headers = {"X-API-Key": self.moralis_api_key}

            logger.info(f"Searching for token {search_term} on chain {chain} via Moralis")

            # Make API request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # Check if we got any results
                    if "result" in data and data["result"]:
                        # Get the first result
                        token = data["result"][0]

                        # Extract token data
                        address = token.get("address")
                        symbol = token.get("symbol")
                        name = token.get("name")

                        if address and symbol:
                            logger.info(f"Found token {symbol} ({name}) at {address}")
                            return address, symbol, name
                else:
                    logger.warning(f"Moralis API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error looking up token with Moralis: {str(e)}")

        return None, None, None
    
    async def _lookup_token_coingecko(
        self, 
        token_symbol: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using CoinGecko API."""
        try:
            search_term = token_symbol.lower()
            url = self._construct_coingecko_url(search_term)
            logger.info(f"Searching for token {search_term} via CoinGecko")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                return await self._parse_coingecko_response(response, client)

        except Exception as e:
            logger.error(f"Error looking up token with CoinGecko: {str(e)}")

        return None, None, None

    def _construct_coingecko_url(self, search_term: str) -> str:
        """Construct the CoinGecko API URL for searching a token."""
        # Always use api.coingecko.com as we have a Demo API key
        if self.coingecko_api_key:
            return f"https://api.coingecko.com/api/v3/search?query={search_term}&x_cg_demo_api_key={self.coingecko_api_key}"
        return f"https://api.coingecko.com/api/v3/search?query={search_term}"

    async def _parse_coingecko_response(self, response: httpx.Response, client: httpx.AsyncClient) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse the response from CoinGecko API."""
        if response.status_code != 200:
            logger.warning(f"CoinGecko API error: {response.status_code} - {response.text}")
            return None, None, None

        data = response.json()
        if "coins" in data and data["coins"]:
            token = data["coins"][0]
            return await self._get_token_contract_address(token, client)

        return None, None, None

    async def _get_token_contract_address(self, token: Dict[str, Any], client: httpx.AsyncClient) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get the token contract address from CoinGecko."""
        coin_id = token.get("id")
        symbol = token.get("symbol", "").upper()
        name = token.get("name")

        if not coin_id or not symbol:
            return None, None, None

        contract_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        contract_response = await client.get(contract_url)

        if contract_response.status_code == 200:
            contract_data = contract_response.json()
            address = contract_data.get("platforms", {}).get("ethereum")

            if address and is_address(address):
                logger.info(f"Found token {symbol} ({name}) at {address}")
                return address, symbol, name

        return None, None, None
    
    async def _lookup_token_quicknode(
        self, 
        token_symbol: str, 
        chain_id: int
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using QuickNode API."""
        if not self.quicknode_api_key:
            logger.warning("QuickNode API key not set")
            return None, None, None
        
        try:
            # Prepare API URL
            search_term = token_symbol.lower()
            url = f"https://api.quicknode.com/chains/{chain_id}/tokens/search?query={search_term}"
            
            # Prepare headers
            headers = {"x-api-key": self.quicknode_api_key}
            
            logger.info(f"Searching for token {search_term} on chain {chain_id} via QuickNode")
            
            # Make API request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we got any results
                    if data.get("success") and data.get("tokens"):
                        # Get the first result
                        token = data["tokens"][0]
                        
                        # Extract token data
                        address = token.get("address")
                        symbol = token.get("symbol")
                        name = token.get("name")
                        
                        if address and symbol:
                            logger.info(f"Found token {symbol} ({name}) at {address}")
                            return address, symbol, name
                else:
                    logger.warning(f"QuickNode API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error looking up token with QuickNode: {str(e)}")
        
        return None, None, None
    
    async def _get_token_metadata_by_address(
        self, 
        address: str, 
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token metadata for a contract address."""
        # Try various sources for metadata
        metadata = await self._get_metadata_from_moralis(address, chain_id) or await self._get_metadata_from_quicknode(address, chain_id)
        
        if metadata:
            # Cache the result
            CONTRACT_CACHE[(address, chain_id)] = (metadata["symbol"], metadata["name"])
        
        return metadata
    
    async def _get_metadata_from_moralis(
        self, 
        address: str, 
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token metadata from Moralis API."""
        if not self.moralis_api_key:
            return None

        try:
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

            # Prepare API URL - use the correct v2.2 endpoint
            url = "https://deep-index.moralis.io/api/v2.2/erc20/metadata"
            params = {
                "chain": chain,
                "addresses": address
            }

            # Prepare headers
            headers = {"X-API-Key": self.moralis_api_key}

            # Make API request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()

                    if data and isinstance(data, list) and len(data) > 0:
                        token = data[0]
                        return {
                            "symbol": token.get("symbol"),
                            "name": token.get("name"),
                            "decimals": token.get("decimals", 18)
                        }
                else:
                    logger.warning(f"Moralis API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error getting metadata from Moralis: {str(e)}")

        return None
    
    async def _get_metadata_from_quicknode(
        self, 
        address: str, 
        chain_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get token metadata from QuickNode API."""
        if not self.quicknode_api_key:
            return None
        
        try:
            # Prepare API URL
            url = f"https://api.quicknode.com/chains/{chain_id}/tokens/{address}"
            
            # Prepare headers
            headers = {"x-api-key": self.quicknode_api_key}
            
            # Make API request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success") and data.get("token"):
                        token = data["token"]
                        return {
                            "symbol": token.get("symbol"),
                            "name": token.get("name"),
                            "decimals": token.get("decimals", 18)
                        }
        
        except Exception as e:
            logger.error(f"Error getting metadata from QuickNode: {str(e)}")
        
        return None

    async def get_token_price(self, token_symbol: str, quote_currency: str = "usd", chain_id: int = 1) -> Tuple[Optional[float], int]:
        """
        Get the price of a token in USD.
        
        Args:
            token_symbol: The token symbol
            quote_currency: The currency to get the price in (default: usd)
            chain_id: The chain ID
            
        Returns:
            Tuple of (price_per_token, token_decimals) where token_decimals is always an int
        """
        from app.services.prices import price_service  # Lazy import to avoid circular dependency

        try:
            # Get the price using the consolidated price_service
            price_data = await price_service.get_token_price(token_symbol, quote_currency, chain_id)
            
            if price_data:
                price = price_data.get("price")
                decimals = price_data.get("decimals", TOKEN_DECIMALS.get(token_symbol.upper(), 18))
                
                # Ensure decimals is an int (not None)
                if decimals is None:
                    decimals = TOKEN_DECIMALS.get(token_symbol.upper(), 18)
                    
                return price, decimals
            
            return None, TOKEN_DECIMALS.get(token_symbol.upper(), 18)
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            # Return None for price but always return an int for decimals
            return None, TOKEN_DECIMALS.get(token_symbol.upper(), 18)

    async def _lookup_token_by_symbol_openocean(
        self,
        token_symbol: str,
        chain_id: int
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Look up token using OpenOcean API with improved matching."""
        try:
            # Map chain ID to OpenOcean chain name
            chain_mapping = {
                1: "eth",
                10: "optimism",
                137: "polygon",
                42161: "arbitrum",
                8453: "base",
                534352: "scroll"
            }
            chain = chain_mapping.get(chain_id)
            if not chain:
                logger.warning(f"Chain {chain_id} not supported by OpenOcean")
                return None, None, None

            # Get token list from OpenOcean
            url = f"https://open-api.openocean.finance/v4/{chain}/tokenList"
            logger.info(f"Searching for token {token_symbol} on chain {chain} via OpenOcean")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data["code"] == 200 and "data" in data:
                        tokens = data["data"]
                        # Clean up search symbol - remove $ and spaces, convert to uppercase
                        search_symbol = token_symbol.strip().lstrip('$').upper()
                        logger.info(f"Searching for cleaned symbol: {search_symbol}")
                        
                        # First try exact match
                        for token in tokens:
                            if token["symbol"].upper() == search_symbol:
                                address = token.get("address")
                                symbol = token.get("symbol")
                                name = token.get("name")
                                if address and symbol:
                                    logger.info(f"Found exact match for token {symbol} ({name}) at {address} via OpenOcean")
                                    return address, symbol, name
                        
                        # If no exact match, try fuzzy matching
                        potential_matches = []
                        for token in tokens:
                            token_symbol = token["symbol"].upper()
                            # Check if search term is contained in token symbol or vice versa
                            if search_symbol in token_symbol or token_symbol in search_symbol:
                                potential_matches.append(token)
                        
                        if potential_matches:
                            # Sort by length difference to find closest match
                            potential_matches.sort(key=lambda x: abs(len(x["symbol"]) - len(search_symbol)))
                            best_match = potential_matches[0]
                            address = best_match.get("address")
                            symbol = best_match.get("symbol")
                            name = best_match.get("name")
                            if address and symbol:
                                logger.info(f"Found fuzzy match for token {symbol} ({name}) at {address} via OpenOcean")
                                return address, symbol, name
                        
                        logger.warning(f"No matches found for token {token_symbol} in OpenOcean token list")
                    else:
                        logger.warning(f"Invalid response format from OpenOcean: {data}")
                else:
                    logger.warning(f"OpenOcean API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error looking up token with OpenOcean: {str(e)}")

        return None, None, None

    def _get_chain_name(self, chain_id: int) -> str:
        """Get a human-readable chain name from a chain ID."""
        chain_names = {
            1: "Ethereum",
            10: "Optimism",
            56: "BNB Chain",
            137: "Polygon",
            42161: "Arbitrum",
            8453: "Base",
            534352: "Scroll"
        }
        return chain_names.get(chain_id, f"chain {chain_id}")

    async def get_token_decimals(self, token_address: str, chain_id: int) -> int:
        """Get the number of decimals for a token."""
        # First check if we have it in our predefined decimals
        if chain_id in TOKEN_DECIMALS and token_address in TOKEN_DECIMALS[chain_id]:
            return TOKEN_DECIMALS[chain_id][token_address]

        try:
            # Try to get decimals from the contract
            if self.quicknode_api_key and chain_id in self.quicknode_endpoints:
                # Use QuickNode to query the contract
                async with httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0) as client:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{
                            "to": token_address,
                            "data": "0x313ce567"  # decimals() function signature
                        }, "latest"],
                        "id": 1
                    }

                    response = await client.post(
                        self.quicknode_endpoints[chain_id],
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if "result" in result and result["result"]:
                            # Convert hex result to int
                            return int(result["result"], 16)

            # If we couldn't get decimals from the contract, try Moralis
            if self.moralis_api_key and chain_id in self.chain_mapping:
                chain_name = self.chain_mapping[chain_id]
                url = "https://deep-index.moralis.io/api/v2.2/erc20/metadata"
                params = {
                    "chain": chain_name,
                    "addresses": [token_address]
                }
                headers = {"X-API-Key": self.moralis_api_key}

                async with httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0) as client:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            return int(data[0].get("decimals", 18))

        except Exception as e:
            logger.error(f"Error getting decimals for token {token_address}: {e}")

        # Default to 18 decimals if we couldn't get it from anywhere
        return 18

    async def get_token_symbol(self, token_address: str, chain_id: int) -> Optional[str]:
        """
        Get the symbol for a token by its address.
        
        Args:
            token_address: The token address
            chain_id: The blockchain ID
            
        Returns:
            The token symbol or None if not found
        """
        logger.info(f"Getting symbol for token at address {token_address} on chain {chain_id}")
        
        # Check predefined token addresses
        for chain_tokens in TOKEN_ADDRESSES.values():
            for symbol, address in chain_tokens.items():
                if address.lower() == token_address.lower():
                    logger.info(f"Found symbol {symbol} for address {token_address} in predefined tokens")
                    return symbol
        
        # If not found in predefined tokens, try to get it from the token metadata
        try:
            # Use the token lookup function that already exists
            _, symbol, _, _ = await self._lookup_token_by_address(token_address, chain_id)
            if symbol:
                logger.info(f"Found symbol {symbol} for address {token_address}")
                return symbol
                
            # If still not found, try to query the contract directly
            if self.quicknode_api_key and chain_id in self.quicknode_endpoints:
                # Use QuickNode to query the contract's symbol() function
                async with httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0) as client:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{
                            "to": token_address,
                            "data": "0x95d89b41"  # symbol() function signature
                        }, "latest"],
                        "id": 1
                    }
                    
                    response = await client.post(
                        self.quicknode_endpoints[chain_id],
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "result" in data and data["result"] and data["result"] != "0x":
                            # Symbol is encoded as bytes32, decode it
                            symbol_hex = data["result"][2:]  # Remove 0x prefix
                            # Parse hex string to bytes, then to utf-8 string
                            symbol_bytes = bytes.fromhex(symbol_hex.replace("0x", ""))
                            # Remove null bytes and decode
                            symbol = symbol_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
                            logger.info(f"Retrieved symbol {symbol} for address {token_address} from contract")
                            return symbol
            
            # If we still couldn't find the symbol, return a generic name based on the address
            short_address = f"{token_address[:6]}...{token_address[-4:]}"
            logger.warning(f"Could not find symbol for {token_address}, using shortened address")
            return short_address
            
        except Exception as e:
            logger.error(f"Error getting token symbol for {token_address}: {e}")
            # Return a generic name based on the address as fallback
            short_address = f"{token_address[:6]}...{token_address[-4:]}"
            return short_address

# Export a singleton instance
token_service = TokenService() 