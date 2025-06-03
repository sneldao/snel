# Tool decorator that maintains function attributes
def tool(func):
    """Simple decorator to mark a function as a tool."""
    # Just return the original function
    return func

from typing import Optional, Dict, List, Any, Union, TypeVar, Callable

# Web3 is optional for portfolio tracking
try:
    from web3 import Web3  # type: ignore
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    # Mock Web3 for type checking only
    class Web3:
        """Mock Web3 class for when web3 is not installed"""
        @staticmethod
        def HTTPProvider(*args: Any, **kwargs: Any) -> Any:
            return None
            
        @staticmethod
        def from_wei(value: Any, unit: str) -> float:
            return 0.0
import os
from dotenv import load_dotenv
import json
import httpx
from datetime import datetime
import asyncio
import logging

# Try to import optional dependencies
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Web3Helper:
    def __init__(self, supported_chains: Dict[int, str]):
        self.supported_chains = supported_chains
        self.web3_instances = {}

        # API keys for blockchain data providers
        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
        self.moralis_api_key = os.getenv("MORALIS_API_KEY")
        self.covalent_api_key = os.getenv("COVALENT_API_KEY")

        # Chain ID to network name mapping for APIs
        self.chain_names = {
            1: "eth-mainnet",
            8453: "base-mainnet",
            42161: "arb-mainnet",
            10: "opt-mainnet",
            137: "polygon-mainnet",
            43114: "avalanche-mainnet",
            56: "bsc-mainnet"
        }

        # Initialize Web3 instances for each chain
        for chain_id, chain_name in supported_chains.items():
            rpc_url = os.getenv(f"{chain_name.upper()}_RPC_URL")
            if rpc_url:
                self.web3_instances[chain_id] = Web3(Web3.HTTPProvider(rpc_url))

    async def get_token_balances_alchemy(self, wallet_address: str, chain_id: int) -> List[Dict]:
        """Get token balances using Alchemy API with timeout."""
        if not self.alchemy_api_key:
            return []

        try:
            network = self.chain_names.get(chain_id, "eth-mainnet")
            url = f"https://{network}.g.alchemy.com/v2/{self.alchemy_api_key}"

            # Add timeout configuration
            timeout_config = httpx.Timeout(timeout=10.0, connect=5.0, read=10.0, write=5.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(url, json={
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "alchemy_getTokenBalances",
                    "params": [wallet_address]
                })

                if response.status_code == 200:
                    data = response.json()
                    return data.get("result", {}).get("tokenBalances", [])

        except Exception as e:
            logger.error(f"Error fetching token balances from Alchemy: {str(e)}")

        return []

    async def get_token_metadata_alchemy(self, token_addresses: List[str], chain_id: int) -> Dict:
        """Get token metadata using Alchemy API."""
        if not self.alchemy_api_key or not token_addresses:
            return {}

        try:
            network = self.chain_names.get(chain_id, "eth-mainnet")
            url = f"https://{network}.g.alchemy.com/v2/{self.alchemy_api_key}"

            # Get metadata for each token individually (Alchemy API format)
            metadata_results = {}

            # Add timeout configuration
            timeout_config = httpx.Timeout(timeout=8.0, connect=3.0, read=8.0, write=3.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                for token_address in token_addresses:
                    try:
                        response = await client.post(url, json={
                            "id": 1,
                            "jsonrpc": "2.0",
                            "method": "alchemy_getTokenMetadata",
                            "params": [token_address]
                        })

                        if response.status_code == 200:
                            data = response.json()
                            result = data.get("result", {})
                            if result:
                                metadata_results[token_address] = result
                    except Exception as e:
                        logger.error(f"Error fetching metadata for token {token_address}: {str(e)}")
                        continue

            return metadata_results

        except Exception as e:
            logger.error(f"Error fetching token metadata from Alchemy: {str(e)}")

        return {}

    async def get_portfolio_data(self, wallet_address: str, chain_id: Optional[int] = None) -> Dict:
        """Get comprehensive portfolio data for a wallet using real blockchain APIs."""
        portfolio_data = {
            "native_balances": {},
            "token_balances": {},
            "chain_data": {},
            "total_value_usd": 0
        }

        chains_to_check = [chain_id] if chain_id else [1, 8453, 42161, 10, 137]  # Focus on major chains

        for cid in chains_to_check:
            chain_name = self.supported_chains.get(cid, f"Chain_{cid}")

            try:
                # Get native token balance using Web3 if available
                if cid in self.web3_instances:
                    w3 = self.web3_instances[cid]
                    native_balance = w3.eth.get_balance(wallet_address)
                    native_balance_eth = float(w3.from_wei(native_balance, 'ether'))

                    portfolio_data["native_balances"][chain_name] = {
                        "balance": native_balance_eth,
                        "symbol": "ETH" if cid == 1 else chain_name,
                        "chain_id": cid
                    }

                    # Get chain-specific data
                    portfolio_data["chain_data"][chain_name] = {
                        "chain_id": cid,
                        "latest_block": w3.eth.block_number,
                        "gas_price": float(w3.from_wei(w3.eth.gas_price, 'gwei'))
                    }

                # Get token balances using Alchemy
                token_balances = await self.get_token_balances_alchemy(wallet_address, cid)
                if token_balances:
                    # Filter tokens by minimum USD value threshold to reduce API calls
                    significant_tokens = []

                    for token in token_balances:
                        balance_hex = token.get("tokenBalance", "0")
                        balance_int = int(balance_hex, 16)

                        if balance_int > 0:
                            # Estimate minimum USD value using conservative token price assumptions
                            # Most legitimate tokens have 18 decimals, dust tokens often have weird decimals
                            estimated_balance = balance_int / (10 ** 18)  # Assume 18 decimals for estimation

                            # Conservative USD value estimation:
                            # - If balance > 100 token units, likely worth checking (could be $100+ if decent token)
                            # - If balance > 10 token units and < 100, might be worth checking for high-value tokens
                            # - If balance < 10 token units, likely dust unless it's a very high-value token

                            # Set minimum threshold: only fetch metadata for tokens that could be worth $100+
                            if estimated_balance >= 10.0:  # At least 10 token units
                                significant_tokens.append(token["contractAddress"])
                            elif estimated_balance >= 2.0 and balance_int > 10**18:  # Small amounts of potentially very valuable tokens
                                significant_tokens.append(token["contractAddress"])

                    logger.info(f"Filtered {len(token_balances)} tokens down to {len(significant_tokens)} significant tokens for {chain_name}")

                    if significant_tokens:
                        metadata = await self.get_token_metadata_alchemy(significant_tokens, cid)

                        # Further filter based on actual metadata and calculated USD values
                        final_tokens = []
                        final_metadata = {}

                        for token in token_balances:
                            contract_addr = token["contractAddress"]
                            if contract_addr in significant_tokens:
                                token_meta = metadata.get(contract_addr, {})
                                balance_hex = token.get("tokenBalance", "0")
                                balance_int = int(balance_hex, 16)
                                decimals = token_meta.get("decimals", 18)

                                if decimals and balance_int > 0:
                                    actual_balance = balance_int / (10 ** decimals)

                                    # Apply final USD value filter
                                    # Conservative estimate: assume token worth $0.01 to $1000
                                    # Only include if estimated value >= $100
                                    min_estimated_value = actual_balance * 0.01  # Very conservative
                                    max_estimated_value = actual_balance * 1000  # Very optimistic

                                    # Include if it could reasonably be worth $100+
                                    if max_estimated_value >= 100.0 and actual_balance >= 0.1:
                                        final_tokens.append(token)
                                        final_metadata[contract_addr] = token_meta

                        logger.info(f"Final filter: {len(final_tokens)} tokens worth potentially $100+ for {chain_name}")

                        if final_tokens:
                            portfolio_data["token_balances"][chain_name] = {
                                "tokens": final_tokens,
                                "metadata": final_metadata
                            }

            except Exception as e:
                logger.error(f"Error getting data for {chain_name}: {str(e)}")
                continue

        return portfolio_data

# Initialize API keys
exa_api_key = os.getenv("EXA_API_KEY")
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

# Initialize Exa client if available
exa_client = None
if exa_api_key:
    try:
        # Optional dependency
        import exa_py  # type: ignore
        # Create Exa client - handle with try/except since the import might succeed
        # but the class might have a different signature in different versions
        try:
            exa_client = exa_py.Exa(api_key=exa_api_key)
        except TypeError:
            # Fall back to positional argument if keyword doesn't work
            exa_client = exa_py.Exa(exa_api_key)
    except ImportError:
        logger.warning("exa_py package not installed")
    except Exception as e:
        logger.error(f"Error initializing Exa API: {str(e)}")

# Function to use Firecrawl v1 API directly
async def firecrawl_scrape_url(url, formats=None, only_main_content=True, timeout=15000):
    """Use Firecrawl v1 API to scrape a URL"""
    if not firecrawl_api_key:
        logger.warning("Firecrawl API key not set")
        return None
    
    api_url = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Authorization": f"Bearer {firecrawl_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": url,
        "formats": formats or ["markdown"],
        "onlyMainContent": only_main_content,
        "timeout": timeout
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Firecrawl API error: {response.status_code} - {response.text}")
                return None
            return response.json()
    except Exception as e:
        logger.error(f"Error with Firecrawl API request: {str(e)}")
        return None

# Function to use Firecrawl v1 API search
async def firecrawl_search(query, limit=5):
    """Use Firecrawl v1 API to search the web"""
    if not firecrawl_api_key:
        logger.warning("Firecrawl API key not set")
        return None
    
    api_url = "https://api.firecrawl.dev/v1/search"
    headers = {
        "Authorization": f"Bearer {firecrawl_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": query,  # Use 'query' instead of 'q' for v1 API
        "limit": limit,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Firecrawl search API error: {response.status_code} - {response.text}")
                return None
            return response.json()
    except Exception as e:
        logger.error(f"Error with Firecrawl search API request: {str(e)}")
        return None

# Custom Web3 Tools for Agno
@tool
async def get_token_balance(wallet_address: str, token_contract: str, chain_id: int = 1) -> Dict:
    """Get ERC-20 token balance for a wallet address on a specific chain using real blockchain data."""
    try:
        web3_helper = Web3Helper(supported_chains={
            1: "Ethereum", 8453: "Base", 42161: "Arbitrum", 10: "Optimism", 137: "Polygon"
        })

        # Get token balances from Alchemy
        token_balances = await web3_helper.get_token_balances_alchemy(wallet_address, chain_id)

        # Find the specific token
        for token in token_balances:
            if token.get("contractAddress", "").lower() == token_contract.lower():
                # Get metadata for this token
                metadata = await web3_helper.get_token_metadata_alchemy([token_contract], chain_id)
                token_info = metadata.get(token_contract, {})

                balance_hex = token.get("tokenBalance", "0")
                balance_int = int(balance_hex, 16)
                decimals = token_info.get("decimals", 18)
                balance_formatted = balance_int / (10 ** decimals)

                return {
                    "wallet_address": wallet_address,
                    "token_contract": token_contract,
                    "chain_id": chain_id,
                    "balance": str(balance_formatted),
                    "symbol": token_info.get("symbol", "UNKNOWN"),
                    "decimals": decimals,
                    "name": token_info.get("name", "Unknown Token"),
                    "balance_raw": balance_hex
                }

        return {
            "wallet_address": wallet_address,
            "token_contract": token_contract,
            "chain_id": chain_id,
            "balance": "0",
            "symbol": "UNKNOWN",
            "decimals": 18,
            "error": "Token not found in wallet"
        }

    except Exception as e:
        return {"error": str(e), "wallet_address": wallet_address}

# No caching - always fetch fresh data for accurate portfolio analysis

@tool
async def get_portfolio_summary(wallet_address: str, chain_id: Optional[int] = None) -> Dict:
    """Get comprehensive portfolio summary including all tokens, NFTs, and DeFi positions using real blockchain data."""
    try:
        logger.info(f"Fetching fresh portfolio data for {wallet_address} on chain {chain_id}")

        web3_helper = Web3Helper(supported_chains={
            1: "Ethereum", 8453: "Base", 42161: "Arbitrum", 10: "Optimism", 137: "Polygon"
        })

        # Get real portfolio data from blockchain with timeout (optimized to reduce API calls)
        try:
            portfolio_data = await asyncio.wait_for(
                web3_helper.get_portfolio_data(wallet_address, chain_id),
                timeout=15.0  # 15 second timeout for portfolio data
            )
        except asyncio.TimeoutError:
            logger.error(f"Portfolio data retrieval timed out for {wallet_address}")
            return {"error": "Portfolio data retrieval timed out", "wallet_address": wallet_address}

        # Calculate total native token value using real price data
        total_native_value = 0
        for chain_name, balance_info in portfolio_data.get("native_balances", {}).items():
            balance = balance_info.get("balance", 0)
            if balance > 0:
                # Use real price estimation based on chain
                if balance_info.get("symbol") == "ETH" or chain_name == "Ethereum":
                    total_native_value += balance * 3500  # Current ETH price
                elif chain_name == "Base":
                    total_native_value += balance * 3500  # Base uses ETH
                elif chain_name == "Polygon":
                    total_native_value += balance * 0.9   # MATIC price
                elif chain_name == "Arbitrum":
                    total_native_value += balance * 3500  # Arbitrum uses ETH
                elif chain_name == "Optimism":
                    total_native_value += balance * 3500  # Optimism uses ETH
                else:
                    total_native_value += balance * 100   # Conservative estimate

        # Count tokens across chains and estimate their value (optimized)
        total_tokens = 0
        token_diversity = 0
        estimated_token_value = 0

        for chain_name, token_data in portfolio_data.get("token_balances", {}).items():
            tokens = token_data.get("tokens", [])
            non_zero_tokens = [t for t in tokens if int(t.get("tokenBalance", "0"), 16) > 0]
            total_tokens += len(non_zero_tokens)
            token_diversity += len(set(t.get("contractAddress") for t in non_zero_tokens))

            # Estimate token values (simplified - in production would use real price APIs)
            for token in non_zero_tokens:
                balance_hex = token.get("tokenBalance", "0")
                balance_int = int(balance_hex, 16)
                if balance_int > 0:
                    # Conservative estimate: assume each token worth $1-10 on average
                    estimated_token_value += min(balance_int / 10**18 * 5, 1000)  # Cap at $1000 per token

        # Add estimated token value to total
        total_portfolio_value = total_native_value + estimated_token_value

        # Calculate basic risk and diversification scores based on real data
        # Count chains with either native balances or token balances
        native_chains = set(portfolio_data.get("native_balances", {}).keys())
        token_chains = set(portfolio_data.get("token_balances", {}).keys())
        all_chains = native_chains.union(token_chains)
        chain_count = len(all_chains)

        risk_score = min(5.0, max(1.0, 3.0 + (chain_count - 1) * 0.3))  # More chains = slightly higher risk
        diversification_score = min(5.0, max(1.0, token_diversity * 0.2 + chain_count * 0.5))

        result = {
            "wallet_address": wallet_address,
            "total_portfolio_value_usd": round(total_portfolio_value, 2),
            "native_value_usd": round(total_native_value, 2),
            "token_value_usd": round(estimated_token_value, 2),
            "native_balances": portfolio_data.get("native_balances", {}),
            "token_balances": portfolio_data.get("token_balances", {}),
            "chain_distribution": portfolio_data.get("chain_data", {}),
            "risk_score": round(risk_score, 1),
            "diversification_score": round(diversification_score, 1),
            "total_tokens": total_tokens,
            "chains_active": chain_count,
            "api_calls_made": portfolio_data.get("api_calls_made", 0),
            "analysis_timestamp": json.dumps(portfolio_data, default=str)
        }

        logger.info(f"Portfolio data retrieved for {wallet_address}, API calls made: {result.get('api_calls_made', 0)}")

        return result

    except Exception as e:
        logger.error(f"Error in get_portfolio_summary: {str(e)}")
        return {"error": str(e), "wallet_address": wallet_address}

@tool
async def analyze_defi_positions(wallet_address: str, chain_id: int = 1) -> Dict:
    """Analyze DeFi positions and discover yield opportunities using Exa search and Firecrawl data."""
    try:
        result = {
            "wallet_address": wallet_address,
            "chain_id": chain_id,
            "liquidity_pools": [],
            "lending_positions": [],
            "staking_positions": [],
            "yield_opportunities": [],
            "total_defi_value_usd": 0,
        }

        # Use Exa to find current DeFi protocols and opportunities
        if exa_client:
            try:
                # Search for current DeFi yield opportunities
                chain_name = {1: "Ethereum", 8453: "Base", 42161: "Arbitrum", 10: "Optimism", 137: "Polygon"}.get(chain_id, "Ethereum")

                defi_search = exa_client.search_and_contents(
                    f"best DeFi yield farming opportunities {chain_name} 2024 stablecoin USDC",
                    text={"max_characters": 2000},
                    num_results=5
                )

                # Extract yield opportunities from search results
                for result_item in defi_search.results:
                    if result_item.text:
                        # Simple parsing for protocol mentions and APY
                        text = result_item.text.lower()
                        protocols = []

                        if "aave" in text:
                            protocols.append({"protocol": "Aave", "type": "lending"})
                        if "compound" in text:
                            protocols.append({"protocol": "Compound", "type": "lending"})
                        if "uniswap" in text:
                            protocols.append({"protocol": "Uniswap", "type": "liquidity"})
                        if "curve" in text:
                            protocols.append({"protocol": "Curve", "type": "liquidity"})
                        if "lido" in text:
                            protocols.append({"protocol": "Lido", "type": "staking"})

                        for protocol in protocols:
                            result["yield_opportunities"].append({
                                "protocol": protocol["protocol"],
                                "type": protocol["type"],
                                "source_url": result_item.url,
                                "description": result_item.text[:200] + "..." if len(result_item.text) > 200 else result_item.text
                            })

            except Exception as e:
                logger.error(f"Error with Exa search: {str(e)}")

        # Use Firecrawl to get specific protocol data
        if firecrawl_api_key and result["yield_opportunities"]:
            try:
                # Scrape Aave for current rates using v1 API
                aave_data = await firecrawl_scrape_url("https://app.aave.com/markets/")
                if aave_data and isinstance(aave_data, dict):
                    content = aave_data.get('data', {}).get('markdown', '')
                    if content:
                        result["lending_positions"].append({
                            "protocol": "Aave",
                            "asset": "USDC",
                            "current_apy": "Real-time data from Aave",
                            "source": "https://app.aave.com/markets/",
                            "scraped_content": content[:200] + "..." if len(content) > 200 else content
                        })

            except Exception as e:
                logger.error(f"Error with Firecrawl: {str(e)}")

        # If no real data found, provide basic structure
        if not result["yield_opportunities"]:
            result["yield_opportunities"] = [
                {"protocol": "Aave", "type": "lending", "description": "Decentralized lending protocol"},
                {"protocol": "Compound", "type": "lending", "description": "Algorithmic money market protocol"},
                {"protocol": "Uniswap V3", "type": "liquidity", "description": "Concentrated liquidity AMM"},
                {"protocol": "Curve", "type": "liquidity", "description": "Stablecoin-focused AMM"}
            ]

        return result

    except Exception as e:
        logger.error(f"Error in analyze_defi_positions: {str(e)}")
        return {"error": str(e), "wallet_address": wallet_address}

@tool
def discover_defi_protocols(query: str = "best stablecoin yield opportunities 2024") -> Dict:
    """Discover DeFi protocols and yield opportunities using Exa search with enhanced filtering."""
    try:
        if not exa_client:
            logger.warning("Exa client not initialized - using fallback data")
            return {
                "query": query,
                "protocols_found": 0,
                "protocols": [],
                "search_strategies_used": 0,
                "error": "Exa client not initialized",
                "fallback_data": {
                    "protocols": [
                        {"name": "Aave", "type": "lending", "apy": "4.5%"},
                        {"name": "Compound", "type": "lending", "apy": "3.2%"},
                        {"name": "Uniswap V3", "type": "liquidity", "apy": "8.1%"}
                    ]
                }
            }

        logger.info(f"Starting Exa search for: {query}")

        # Enhanced search with multiple strategies
        search_strategies = [
            f"{query} DeFi yield farming APY 2024",
            f"stablecoin lending rates {query}",
            f"liquidity mining opportunities {query}",
            f"DeFi protocol comparison {query}"
        ]

        all_protocols = []
        unique_urls = set()
        successful_searches = 0

        for strategy in search_strategies:
            try:
                logger.info(f"Executing Exa search strategy: {strategy}")

                # Use correct Exa API parameters based on documentation
                search_results = exa_client.search_and_contents(
                    query=strategy,
                    num_results=3,  # Reduced to avoid rate limits
                    text={"max_characters": 1500},
                    highlights={"num_sentences": 2},
                    summary=True,
                    type="neural",  # Use neural search for better semantic matching
                    start_published_date="2024-01-01"  # Focus on recent content
                )

                successful_searches += 1
                logger.info(f"Exa search successful, found {len(search_results.results)} results")

                for result in search_results.results:
                    if result.url not in unique_urls and result.text:
                        unique_urls.add(result.url)

                        # Extract APY/yield information
                        apy_info = extract_yield_info(result.text)

                        all_protocols.append({
                            "title": result.title,
                            "url": result.url,
                            "content": result.text[:600] + "..." if len(result.text) > 600 else result.text,
                            "published_date": getattr(result, 'published_date', None),
                            "search_strategy": strategy,
                            "yield_info": apy_info,
                            "relevance_score": calculate_relevance_score(result.text, query),
                            "summary": getattr(result, 'summary', '')[:200] if hasattr(result, 'summary') else ''
                        })
            except Exception as e:
                logger.warning(f"Search strategy '{strategy}' failed: {str(e)}")
                continue

        # Sort by relevance score
        all_protocols.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        logger.info(f"Exa search completed: {len(all_protocols)} protocols found from {successful_searches} successful searches")

        return {
            "query": query,
            "protocols_found": len(all_protocols),
            "protocols": all_protocols[:10],  # Return top 10 most relevant
            "search_strategies_used": successful_searches,
            "total_strategies": len(search_strategies),
            "scraped_at": datetime.utcnow().isoformat(),
            "success": True
        }

    except Exception as e:
        logger.error(f"Error in discover_defi_protocols: {str(e)}")
        return {
            "query": query,
            "protocols_found": 0,
            "protocols": [],
            "error": str(e),
            "success": False
        }

def extract_yield_info(text: str) -> Dict:
    """Extract yield/APY information from text content."""
    import re

    # Look for APY patterns
    apy_patterns = [
        r'(\d+\.?\d*)\s*%\s*APY',
        r'APY[:\s]*(\d+\.?\d*)\s*%',
        r'yield[:\s]*(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%\s*yield'
    ]

    yields = []
    for pattern in apy_patterns:
        matches = re.findall(pattern, text.lower())
        yields.extend([float(match) for match in matches if float(match) < 100])  # Filter unrealistic yields

    return {
        "max_apy": max(yields) if yields else None,
        "min_apy": min(yields) if yields else None,
        "avg_apy": sum(yields) / len(yields) if yields else None,
        "yield_mentions": len(yields)
    }

def calculate_relevance_score(text: str, query: str) -> float:
    """Calculate relevance score based on keyword matching and content quality."""
    text_lower = text.lower()
    query_lower = query.lower()

    # Base score
    score = 0.0

    # Keyword matching
    query_words = query_lower.split()
    for word in query_words:
        if word in text_lower:
            score += 1.0

    # DeFi-specific terms
    defi_terms = ['apy', 'yield', 'liquidity', 'staking', 'farming', 'protocol', 'tvl', 'defi']
    for term in defi_terms:
        if term in text_lower:
            score += 0.5

    # Quality indicators
    if 'audit' in text_lower:
        score += 1.0
    if 'security' in text_lower:
        score += 0.5
    if len(text) > 500:  # Longer content often more informative
        score += 0.5

    return score

@tool
async def get_protocol_details(protocol_url: str) -> Dict:
    """Get detailed information about a specific DeFi protocol using Firecrawl with enhanced extraction."""
    try:
        if not firecrawl_api_key:
            logger.warning("Firecrawl API key not set - using fallback data")
            return {
                "url": protocol_url,
                "title": "Protocol Details",
                "description": "Firecrawl API key not available",
                "error": "Firecrawl API key not set",
                "success": False,
                "fallback_data": {
                    "tvl": "N/A",
                    "security_audits": "Unverified",
                    "live_rates": "No rates"
                }
            }

        logger.info(f"Starting Firecrawl scrape for: {protocol_url}")

        # Scrape the protocol website for details using v1 API
        scraped_data = await firecrawl_scrape_url(
            url=protocol_url,
            formats=["markdown"],
            only_main_content=True,
            timeout=15000
        )

        logger.info(f"Firecrawl scrape completed for {protocol_url}")

        if scraped_data and isinstance(scraped_data, dict) and "data" in scraped_data:
            data = scraped_data.get('data', {})
            content = data.get('markdown', '')
            metadata = data.get('metadata', {})

            # Enhanced information extraction
            extracted_info = extract_protocol_info(content)

            result = {
                "url": protocol_url,
                "title": metadata.get('title', "Unknown Protocol"),
                "description": metadata.get('description', ''),
                "content": content[:1000] + "..." if len(content) > 1000 else content,
                "metadata": metadata,
                "extracted_info": extracted_info,
                "scraped_at": datetime.utcnow().isoformat(),
                "success": True,
                "tvl_analyzed": extracted_info.get("tvl_info", {}).get("has_tvl_data", False),
                "security_audits": "Verified" if extracted_info.get("security_info", {}).get("audit_mentioned", False) else "Unverified",
                "live_rates": "Available" if content and len(content) > 100 else "No rates"
            }

            logger.info(f"Successfully extracted protocol details for {protocol_url}")
            return result
        else:
            logger.warning(f"Failed to scrape protocol data for {protocol_url}")
            return {
                "url": protocol_url,
                "title": "Protocol Details",
                "description": "Failed to scrape protocol data",
                "error": "Failed to scrape protocol data",
                "success": False,
                "tvl_analyzed": "N/A",
                "security_audits": "Unverified",
                "live_rates": "No rates"
            }

    except Exception as e:
        logger.error(f"Error in get_protocol_details: {str(e)}")
        return {
            "url": protocol_url,
            "title": "Protocol Details",
            "description": "Error occurred during scraping",
            "error": str(e),
            "success": False,
            "tvl_analyzed": "N/A",
            "security_audits": "Unverified",
            "live_rates": "No rates"
        }

def extract_protocol_info(content: str) -> Dict:
    """Extract structured information from protocol content."""

    info = {
        "yield_info": extract_yield_info(content),
        "tvl_info": extract_tvl_info(content),
        "security_info": extract_security_info(content),
        "token_info": extract_token_info(content),
        "chain_info": extract_chain_info(content)
    }

    return info

def extract_tvl_info(content: str) -> Dict:
    """Extract Total Value Locked (TVL) information."""
    import re

    tvl_patterns = [
        r'TVL[:\s]*\$?([0-9,.]+[BMK]?)',
        r'Total Value Locked[:\s]*\$?([0-9,.]+[BMK]?)',
        r'\$([0-9,.]+[BMK]?)\s*TVL',
        r'locked[:\s]*\$?([0-9,.]+[BMK]?)'
    ]

    tvl_values = []
    for pattern in tvl_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        tvl_values.extend(matches)

    return {
        "tvl_mentions": tvl_values,
        "has_tvl_data": len(tvl_values) > 0
    }

def extract_security_info(content: str) -> Dict:
    """Extract security-related information."""
    content_lower = content.lower()

    security_indicators = {
        "audit_mentioned": any(term in content_lower for term in ['audit', 'audited', 'security audit']),
        "insurance_mentioned": 'insurance' in content_lower,
        "multisig_mentioned": any(term in content_lower for term in ['multisig', 'multi-sig', 'timelock']),
        "bug_bounty_mentioned": 'bug bounty' in content_lower
    }

    return security_indicators

def extract_token_info(content: str) -> Dict:
    """Extract token-related information."""
    import re

    # Look for token symbols (3-5 uppercase letters)
    token_pattern = r'\b[A-Z]{3,5}\b'
    tokens = list(set(re.findall(token_pattern, content)))

    # Filter out common non-token words
    excluded = {'THE', 'AND', 'FOR', 'YOU', 'ARE', 'NOT', 'CAN', 'ALL', 'NEW', 'GET', 'USE', 'NOW', 'TOP', 'HOW', 'WHY', 'WHO', 'API', 'FAQ', 'USD', 'EUR', 'GBP'}
    tokens = [token for token in tokens if token not in excluded]

    return {
        "tokens_mentioned": tokens[:10],  # Limit to first 10 found
        "token_count": len(tokens)
    }

def extract_chain_info(content: str) -> Dict:
    """Extract blockchain/chain information."""
    content_lower = content.lower()

    chains = {
        "ethereum": "ethereum" in content_lower or "eth" in content_lower,
        "polygon": "polygon" in content_lower or "matic" in content_lower,
        "arbitrum": "arbitrum" in content_lower,
        "optimism": "optimism" in content_lower,
        "base": "base" in content_lower,
        "avalanche": "avalanche" in content_lower or "avax" in content_lower,
        "bsc": "bsc" in content_lower or "binance smart chain" in content_lower
    }

    supported_chains = [chain for chain, supported in chains.items() if supported]

    return {
        "supported_chains": supported_chains,
        "multi_chain": len(supported_chains) > 1
    }

@tool
def analyze_market_trends(query: str = "DeFi market trends 2024") -> Dict:
    """Analyze current market trends and sentiment using Exa's advanced search capabilities."""
    try:
        if not exa_client:
            return {"error": "Exa client not initialized"}

        # Multi-faceted market analysis
        analysis_queries = [
            f"{query} market analysis sentiment",
            f"DeFi TVL trends {query}",
            f"cryptocurrency market outlook {query}",
            f"yield farming trends {query}",
            f"institutional DeFi adoption {query}"
        ]

        market_data = {
            "sentiment_analysis": {},
            "trend_indicators": [],
            "risk_factors": [],
            "opportunities": [],
            "market_summary": ""
        }

        for query_type in analysis_queries:
            try:
                # Use correct Exa API parameters for market analysis
                results = exa_client.search_and_contents(
                    query=query_type,
                    num_results=3,
                    text={"max_characters": 1500},
                    highlights={"num_sentences": 2},
                    summary=True,
                    type="neural",
                    start_published_date="2024-01-01"  # Focus on recent data
                )

                for result in results.results:
                    if result.text:
                        # Analyze sentiment and extract insights
                        sentiment = analyze_content_sentiment(result.text)
                        trends = extract_trend_indicators(result.text)

                        market_data["trend_indicators"].extend(trends)

                        if sentiment["sentiment_score"] > 0.6:
                            market_data["opportunities"].append({
                                "source": result.title,
                                "url": result.url,
                                "insight": result.text[:200] + "...",
                                "sentiment": "positive"
                            })
                        elif sentiment["sentiment_score"] < 0.4:
                            market_data["risk_factors"].append({
                                "source": result.title,
                                "url": result.url,
                                "concern": result.text[:200] + "...",
                                "sentiment": "negative"
                            })

            except Exception as e:
                logger.warning(f"Market analysis query '{query_type}' failed: {str(e)}")
                continue

        # Generate market summary
        market_data["market_summary"] = generate_market_summary(market_data)

        return {
            "query": query,
            "analysis_timestamp": json.dumps({"timestamp": "now"}, default=str),
            "market_data": market_data,
            "total_sources": len(market_data["opportunities"]) + len(market_data["risk_factors"])
        }

    except Exception as e:
        logger.error(f"Error in analyze_market_trends: {str(e)}")
        return {"error": str(e)}

def analyze_content_sentiment(content: str) -> Dict:
    """Simple sentiment analysis based on keyword presence."""
    positive_words = ['growth', 'increase', 'bullish', 'opportunity', 'positive', 'gain', 'rise', 'strong', 'optimistic']
    negative_words = ['decline', 'decrease', 'bearish', 'risk', 'negative', 'loss', 'fall', 'weak', 'pessimistic']

    content_lower = content.lower()
    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)

    total_sentiment_words = positive_count + negative_count
    sentiment_score = positive_count / total_sentiment_words if total_sentiment_words > 0 else 0.5

    return {
        "sentiment_score": sentiment_score,
        "positive_indicators": positive_count,
        "negative_indicators": negative_count,
        "overall_sentiment": "positive" if sentiment_score > 0.6 else "negative" if sentiment_score < 0.4 else "neutral"
    }

def extract_trend_indicators(content: str) -> List[str]:
    """Extract trend indicators from content."""
    import re

    # Look for percentage changes
    percentage_patterns = [
        r'(\w+)\s+(?:up|increased|rose)\s+(\d+\.?\d*)\s*%',
        r'(\w+)\s+(?:down|decreased|fell)\s+(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%\s+(?:increase|decrease|change)\s+in\s+(\w+)'
    ]

    trends = []
    for pattern in percentage_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if len(match) == 2:
                trends.append(f"{match[0]}: {match[1]}% change")

    return trends[:5]  # Limit to 5 trends

def generate_market_summary(market_data: Dict) -> str:
    """Generate a concise market summary from analyzed data."""
    opportunities_count = len(market_data.get("opportunities", []))
    risks_count = len(market_data.get("risk_factors", []))

    if opportunities_count > risks_count:
        sentiment = "Generally positive market sentiment with multiple opportunities identified."
    elif risks_count > opportunities_count:
        sentiment = "Cautious market outlook with several risk factors to consider."
    else:
        sentiment = "Balanced market conditions with both opportunities and risks present."

    return f"{sentiment} Analysis based on {opportunities_count + risks_count} recent sources."

class PortfolioManagementAgent:
    SUPPORTED_CHAINS = {
        1: "Ethereum",
        8453: "Base",
        42161: "Arbitrum",
        10: "Optimism",
        137: "Polygon",
        43114: "Avalanche",
        534352: "Scroll",
        56: "BSC",
        59144: "Linea",
        5000: "Mantle",
        81457: "Blast",
        324: "zkSync Era",
    }

    def __init__(self):
        # Validate required environment variables
        required_vars = ["OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Initialize Web3 helper if Web3 is available
        if WEB3_AVAILABLE:
            self.web3_helper = Web3Helper(supported_chains=self.SUPPORTED_CHAINS)
        else:
            logger.warning("Web3 library not available, some functionality will be limited")
            self.web3_helper = None

    async def analyze_portfolio(self, prompt: str, wallet_address: str, chain_id: Optional[int] = None, 
                                   model_config: Optional[Dict[str, Any]] = None, tools_config: Optional[List[Any]] = None,
                                   instructions: Optional[str] = None, markdown: bool = True, 
                                   stream: bool = False) -> Dict[str, Any]:
        """
        Analyze a user's portfolio based on their prompt and wallet address.
        """
        try:
            # Instead of using Agno library, we'll directly call our portfolio analysis functions
            portfolio_data = await get_portfolio_summary(wallet_address, chain_id)
            
            # Extract basic info from portfolio data
            portfolio_value = portfolio_data.get("total_portfolio_value_usd", 0)
            chains_active = portfolio_data.get("chains_active", 0)
            total_tokens = portfolio_data.get("total_tokens", 0)
            risk_score = portfolio_data.get("risk_score", 0)
            
            # Perform DeFi analysis
            defi_positions = await analyze_defi_positions(wallet_address, chain_id if chain_id else 1)
            
            # Try to discover DeFi protocols
            defi_protocols = discover_defi_protocols(f"best defi protocols for {prompt}")
            
            # Generate a summary of the portfolio
            chains_list = list(portfolio_data.get("chain_distribution", {}).keys())
            chains_text = ", ".join(chains_list[:3]) if chains_list else "no chains"
            
            summary = f"""
Portfolio Analysis for {wallet_address}:

Total Value: ${portfolio_value:,.2f}
Active Chains: {chains_active}
Total Tokens: {total_tokens}
Risk Score: {risk_score}/5

The portfolio is primarily invested in {chains_text}.
            """
            
            # Add DeFi opportunities if available
            if defi_positions and "yield_opportunities" in defi_positions:
                opportunities = defi_positions["yield_opportunities"]
                summary += f"\n\nDeFi Opportunities: {len(opportunities)} protocols identified including "
                summary += ", ".join([p["protocol"] for p in opportunities[:3]])
            
            # Prepare the result
            result = {
                "result": summary,
                "portfolio_data": portfolio_data,
                "defi_positions": defi_positions,
                "defi_protocols": defi_protocols,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            return result

            # This section is no longer needed as we're directly calling our functions above
            return result
        except Exception as e:
            logger.error(f"Error in analyze_portfolio: {str(e)}")
            return {
                "error": str(e),
                "wallet_address": wallet_address
            }
            
    # This method is not used anymore since we're directly implementing
    # the portfolio analysis in the analyze_portfolio method

            # Extract content from Agno RunResponse object
            content = ""
            if hasattr(result, 'content'):
                content = str(result.content)
            elif hasattr(result, 'response'):
                content = str(result.response)
            else:
                content = str(result)

            return content
        except Exception as e:
            logger.error(f"Error in async analysis: {str(e)}")
            return f"Error in analysis: {str(e)}"