"""
Price service for fetching real-time token prices from CoinGecko API.
"""
import httpx
import asyncio
from typing import Dict, Optional, Any
import os
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class PriceService:
    """Service for fetching real-time token prices."""
    
    def __init__(self):
        """Initialize the price service."""
        self.base_url = "https://api.coingecko.com/api/v3"
        self.http_client = None
        # Token ID mapping for CoinGecko (common tokens)
        self.token_id_mapping = {
            "ETH": "ethereum",
            "WETH": "weth",
            "USDC": "usd-coin",
            "USDT": "tether",
            "DAI": "dai",
            "WBTC": "wrapped-bitcoin",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "BNB": "binancecoin",
            "FTM": "fantom",
            "CRV": "curve-dao-token",
            "LINK": "chainlink",
            "UNI": "uniswap",
            "AAVE": "aave",
            "COMP": "compound-governance-token",
            "SNX": "havven",
            "YFI": "yearn-finance",
            "MKR": "maker",
            "SUSHI": "sushi",
            "BAL": "balancer",
            "1INCH": "1inch",
            "ZRX": "0x",
            "ENJ": "enjincoin",
            "MANA": "decentraland",
            "BAT": "basic-attention-token",
            "LRC": "loopring",
            "REN": "republic-protocol",
            "KNC": "kyber-network-crystal",
            "BNT": "bancor",
            "GNO": "gnosis",
            "OMG": "omisego",
            "ZIL": "zilliqa",
            # MNEE - Real USD-backed stablecoin powered by 1Sat Ordinals and Ethereum
            "MNEE": "mnee",  # Will fallback to USDC if not found on CoinGecko
        }
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=10.0)
        return self.http_client
        
    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            
    async def get_token_price(self, token_symbol: str, currency: str = "usd") -> Optional[Decimal]:
        """
        Get the current price of a token in the specified currency.
        
        Args:
            token_symbol: Token symbol (e.g., "ETH", "USDC")
            currency: Target currency (default: "usd")
            
        Returns:
            Token price as Decimal or None if not found
        """
        try:
            # Get CoinGecko ID for the token
            token_id = self.token_id_mapping.get(token_symbol.upper())
            if not token_id:
                logger.warning(f"No CoinGecko ID found for token: {token_symbol}")
                return None
                
            client = await self._get_client()
            
            # Fetch price from CoinGecko
            response = await client.get(
                f"{self.base_url}/simple/price",
                params={
                    "ids": token_id,
                    "vs_currencies": currency
                }
            )
            
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                # Special fallback for MNEE - use USDC price as it's USD-backed
                if token_symbol.upper() == "MNEE":
                    logger.info("Falling back to USDC price for MNEE")
                    return await self.get_token_price("USDC", currency)
                return None
                
            data = response.json()
            
            if token_id in data and currency in data[token_id]:
                price = data[token_id][currency]
                return Decimal(str(price))
            else:
                logger.warning(f"Price not found for {token_symbol} in {currency}")
                # Special fallback for MNEE - use USDC price as it's USD-backed
                if token_symbol.upper() == "MNEE":
                    logger.info("Falling back to USDC price for MNEE")
                    return await self.get_token_price("USDC", currency)
                return None
                
        except Exception as e:
            logger.error(f"Error fetching price for {token_symbol}: {str(e)}")
            # Special fallback for MNEE - use USDC price as it's USD-backed
            if token_symbol.upper() == "MNEE":
                logger.info("Falling back to USDC price for MNEE due to error")
                return await self.get_token_price("USDC", currency)
            return None
            
    async def convert_usd_to_token_amount(self, usd_amount: Decimal, token_symbol: str) -> Optional[Decimal]:
        """
        Convert a USD amount to token amount based on current price.
        
        Args:
            usd_amount: Amount in USD
            token_symbol: Target token symbol
            
        Returns:
            Token amount as Decimal or None if conversion failed
        """
        try:
            # Get token price
            price = await self.get_token_price(token_symbol)
            if not price or price <= 0:
                logger.error(f"Could not get valid price for {token_symbol}")
                return None
                
            # Convert USD to token amount
            # Formula: token_amount = usd_amount / token_price
            token_amount = usd_amount / price
            return token_amount
            
        except Exception as e:
            logger.error(f"Error converting ${usd_amount} to {token_symbol}: {str(e)}")
            return None
            
    async def get_multiple_token_prices(self, token_symbols: list, currency: str = "usd") -> Dict[str, Optional[Decimal]]:
        """
        Get prices for multiple tokens in one request.
        
        Args:
            token_symbols: List of token symbols
            currency: Target currency (default: "usd")
            
        Returns:
            Dictionary mapping token symbols to prices
        """
        try:
            # Get CoinGecko IDs for all tokens
            token_ids = []
            symbol_to_id = {}
            id_to_symbol = {}
            
            for symbol in token_symbols:
                token_id = self.token_id_mapping.get(symbol.upper())
                if token_id:
                    token_ids.append(token_id)
                    symbol_to_id[symbol.upper()] = token_id
                    id_to_symbol[token_id] = symbol.upper()
            
            if not token_ids:
                return {symbol: None for symbol in token_symbols}
                
            client = await self._get_client()
            
            # Fetch prices from CoinGecko
            response = await client.get(
                f"{self.base_url}/simple/price",
                params={
                    "ids": ",".join(token_ids),
                    "vs_currencies": currency
                }
            )
            
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                return {symbol: None for symbol in token_symbols}
                
            data = response.json()
            result = {}
            
            # Map results back to original symbols
            for symbol in token_symbols:
                token_id = symbol_to_id.get(symbol.upper())
                if token_id and token_id in data and currency in data[token_id]:
                    result[symbol] = Decimal(str(data[token_id][currency]))
                else:
                    result[symbol] = None
                    
            return result
            
        except Exception as e:
            logger.error(f"Error fetching multiple token prices: {str(e)}")
            return {symbol: None for symbol in token_symbols}

# Global instance
price_service = PriceService()