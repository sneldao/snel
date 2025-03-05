from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, validator
from .base import PointlessAgent, AgentMessage
from app.services.token_service import TokenService
from app.services.prices import get_token_price
import logging
import json
import re
import time
import random

logger = logging.getLogger(__name__)

class PriceResponse(BaseModel):
    """Response model for price queries."""
    tokens: List[str]
    vs_currency: str = "USD"
    natural_command: Optional[str] = None
    is_contract_address: bool = False

    @validator("tokens", each_item=True)
    def validate_token(cls, v):
        if not v:
            raise ValueError("Token cannot be empty")
        # Allow contract addresses to pass through without modification
        return v if v.startswith("0x") else v.strip().upper()

    @validator("vs_currency")
    def validate_vs_currency(cls, v):
        if not v:
            raise ValueError("vs_currency cannot be empty")
        return v.strip().upper()

class PriceAgent(PointlessAgent):
    """Agent for processing price queries."""
    token_service: TokenService = Field(default_factory=TokenService)
    
    def __init__(self, prompt: str = "", provider = None):
        if not prompt:
            prompt = "You are a helpful assistant that processes price queries for cryptocurrencies. You extract token names from natural language questions about prices."
        super().__init__(
            prompt=prompt,
            model="gpt-4-turbo-preview",
            temperature=0.7,
            provider=provider
        )

    async def process_price(self, query: str) -> Dict[str, Any]:
        """Process a price query and return structured response."""
        try:
            response = await self.process(query, response_format=PriceResponse)
            
            if response.get("error"):
                return AgentMessage(
                    error=response["error"],
                    metadata={"query": query}
                ).model_dump()

            return AgentMessage(
                content=response["content"],
                metadata={"query": query}
            ).model_dump()

        except Exception as e:
            return AgentMessage(
                error=f"Failed to process price query: {str(e)}",
                metadata={"query": query}
            ).model_dump()

    async def process_price_query(self, input_text: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
        """Process a price query and return structured data."""
        try:
            # Extract tokens directly from the input text if possible
            tokens = self._extract_tokens_from_text(input_text)
            
            if tokens:
                # Use the first token found
                token = tokens[0]
                logger.info(f"Extracted token from text: {token}")
                
                # Get token price
                return await self._get_token_price(token, chain_id or 1)
            
            # If no tokens found directly, try using the LLM
            response = await self.process(input_text, response_format=PriceResponse)
            if response.get("error"):
                return response
            
            # Extract the response content
            data = response.get("content", {})
            if not data.get("tokens"):
                return AgentMessage(
                    error="No tokens found in query",
                    metadata={"query": input_text}
                ).model_dump()
            
            # Extract token (preserve original case and $ prefix)
            original_token = data["tokens"][0]
            
            # Get token price
            return await self._get_token_price(original_token, chain_id or 1)
            
        except Exception as e:
            logger.error(f"Error processing price query: {str(e)}")
            return AgentMessage(
                error=f"Failed to process price query: {str(e)}",
                metadata={"query": input_text}
            ).model_dump()
    
    def _extract_tokens_from_text(self, text: str) -> List[str]:
        """Extract potential token symbols from text."""
        # Common tokens to look for
        common_tokens = [
            "ETH", "BTC", "USDC", "USDT", "DAI", "SOL", "AVAX", "MATIC", 
            "LINK", "UNI", "AAVE", "SNX", "MKR", "COMP", "YFI", "SUSHI",
            "DOGE", "SHIB", "ADA", "DOT", "XRP", "LTC", "BCH", "EOS",
            "XLM", "TRX", "XTZ", "ATOM", "VET", "FIL", "THETA", "XMR",
            "ALGO", "ETC", "ZEC", "DASH", "XEM", "NEO", "ONT", "BAT",
            "ZRX", "REN", "KNC", "CRV", "BAL", "LRC", "MATIC", "GRT",
            "1INCH", "CAKE", "LUNA", "FTM", "NEAR", "ATOM", "RUNE", "FLOW",
            "HBAR", "ONE", "EGLD", "KAVA", "CELO", "ROSE", "MINA", "SCRT",
            "BAND", "ANKR", "STORJ", "OCEAN", "NMR", "ALPHA", "SAND", "MANA",
            "AXS", "ENJ", "CHZ", "ALICE", "GALA", "ILV", "YGG", "SLP",
            "APE", "GMT", "IMX", "LOOKS", "LDO", "CVX", "RPL", "SPELL",
            "PEOPLE", "BTRST", "FORTH", "TRIBE", "RAI", "FEI", "FRAX", "LUSD",
            "GUSD", "BUSD", "TUSD", "USDP", "SUSD", "OUSD", "MUSD", "HUSD",
            "DUSD", "NUSD", "CUSD", "ZUSD", "PUSD", "AUSD", "EUSD", "IUSD",
            "JUSD", "KUSD", "LUSD", "MUSD", "NUSD", "OUSD", "PUSD", "QUSD",
            "RUSD", "SUSD", "TUSD", "UUSD", "VUSD", "WUSD", "XUSD", "YUSD",
            "ZUSD", "WETH", "WBTC", "WBNB", "WAVAX", "WMATIC", "WSOL", "WFTM",
            "WONE", "WGLMR", "WMOVR", "WKAVA", "WCELO", "WROSE", "WMINA", "WSCRT",
            "WBAND", "WANKR", "WSTORJ", "WOCEAN", "WNMR", "WALPHA", "WSAND", "WMANA",
            "WAXS", "WENJ", "WCHZ", "WALICE", "WGALA", "WILV", "WYGG", "WSLP",
            "WAPE", "WGMT", "WIMX", "WLOOKS", "WLDO", "WCVX", "WRPL", "WSPELL",
            "WPEOPLE", "WBTRST", "WFORTH", "WTRIBE", "WRAI", "WFEI", "WFRAX", "WLUSD",
            "BITCOIN", "ETHEREUM", "POLYGON", "AVALANCHE", "SOLANA", "CARDANO", "POLKADOT"
        ]
        
        # Extract tokens from text
        tokens = []
        words = re.findall(r'\b[A-Za-z0-9$]+\b', text.upper())
        
        for word in words:
            # Remove $ prefix if present
            clean_word = word.lstrip('$')
            
            # Check if it's a common token
            if clean_word in common_tokens:
                tokens.append(clean_word)
            
            # Check if it's a contract address
            if word.startswith('0X') and len(word) == 42:
                tokens.append(word.lower())
        
        return tokens
    
    async def _get_token_price(self, token: str, chain_id: int) -> Dict[str, Any]:
        """Get price data for a token."""
        try:
            # Check if it's a contract address
            if token.startswith("0x"):
                logger.info(f"Processing contract address: {token}")
                token_info = await self.token_service.lookup_token(token, chain_id)
                
                if not token_info or not token_info[0]:
                    return AgentMessage(
                        error=f"Could not find token information for contract address {token}",
                        metadata={"token": token}
                    ).model_dump()
                
                address, symbol, name, metadata = token_info
                
                # Try to get the price using the contract address
                price_data = await self._fetch_token_price(symbol, address, chain_id)
                
                return self._format_price_response(symbol, price_data, token_info)
            
            # Regular token symbol
            logger.info(f"Processing token symbol: {token}")
            token_info = await self.token_service.lookup_token(token, chain_id)
            
            if not token_info or not token_info[0]:
                return AgentMessage(
                    error=f"Could not find token information for {token}",
                    metadata={"token": token}
                ).model_dump()
            
            address, symbol, name, metadata = token_info
            
            # Get price data
            price_data = await self._fetch_token_price(symbol, address, chain_id)
            
            return self._format_price_response(symbol, price_data, token_info)
            
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return AgentMessage(
                error=f"Failed to get price for {token}: {str(e)}",
                metadata={"token": token}
            ).model_dump()
    
    async def _fetch_token_price(self, symbol: str, address: Optional[str] = None, chain_id: int = 1) -> Dict[str, Any]:
        """Fetch price data for a token."""
        try:
            # Try to get price from token service
            price, timestamp = await self.token_service.get_token_price(symbol, "usd", chain_id)
            
            if price is not None:
                return {
                    "price": price,
                    "timestamp": timestamp,
                    "source": "token_service"
                }
            
            # Fallback to prices.py functions
            if address:
                price = await get_token_price(symbol, address, chain_id)
                if price and price[0]:
                    return {
                        "price": price[0],
                        "timestamp": int(time.time()),
                        "source": "prices_module"
                    }
            
            return {
                "price": None,
                "error": "Could not fetch price"
            }
            
        except Exception as e:
            logger.error(f"Error fetching token price: {str(e)}")
            return {
                "price": None,
                "error": str(e)
            }
    
    def _format_price_response(self, symbol: str, price_data: Dict[str, Any], token_info: Tuple) -> Dict[str, Any]:
        """Format the price response."""
        address, _, name, metadata = token_info
        
        if price_data.get("price") is None:
            return AgentMessage(
                error=f"Could not fetch price for {symbol}",
                metadata={"token": symbol}
            ).model_dump()
        
        # Format the price message with personality
        price_messages = [
            f"The current price of {symbol} is ${price_data['price']:.2f}. Not that I care much, but thought you'd want to know.",
            f"Looks like {symbol} is worth ${price_data['price']:.2f} right now. Do with that what you will.",
            f"${price_data['price']:.2f} per {symbol}. That's what the internet tells me, anyway.",
            f"{symbol} is trading at ${price_data['price']:.2f}. Buy high, sell low, right?",
            f"I checked, and {symbol} is going for ${price_data['price']:.2f}. Not financial advice, obviously.",
            f"The price of {symbol} is ${price_data['price']:.2f}. But prices are just, like, numbers, man.",
            f"{symbol}: ${price_data['price']:.2f}. Do you want me to pretend to be excited about that?",
            f"I dragged myself all the way to the price API, and {symbol} is at ${price_data['price']:.2f}.",
            f"${price_data['price']:.2f} per {symbol}. I'm sure that means something to someone.",
            f"After extensive research (one API call), I can tell you that {symbol} is worth ${price_data['price']:.2f}."
        ]
        
        # Format the response
        return {
            "content": {
                "type": "price",
                "message": random.choice(price_messages),
                "token": {
                    "symbol": symbol,
                    "name": name,
                    "address": address,
                    "metadata": metadata
                },
                "price": price_data["price"],
                "source": price_data.get("source", "unknown"),
                "timestamp": price_data.get("timestamp", int(time.time()))
            },
            "error": None,
            "metadata": {
                "token": symbol,
                "chain_id": metadata.get("chain_id", 1) if metadata else 1
            }
        }
    
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
    
    def _get_popular_tokens_for_chain(self, chain_id: int) -> List[str]:
        """Get a list of popular tokens for a specific chain."""
        popular_tokens = {
            1: ["ETH", "USDC", "USDT", "DAI", "WBTC"],
            10: ["OP", "ETH", "USDC", "USDT", "DAI"],
            56: ["BNB", "BUSD", "CAKE", "USDT", "USDC"],
            137: ["MATIC", "USDC", "USDT", "DAI", "WETH"],
            42161: ["ARB", "ETH", "USDC", "USDT", "DAI"],
            8453: ["ETH", "USDC", "DAI", "WETH", "CBETH"],
            534352: ["ETH", "USDC", "USDT", "DAI", "SCR"]
        }
        return popular_tokens.get(chain_id, []) 