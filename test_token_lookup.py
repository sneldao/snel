import httpx
import asyncio
from typing import Optional, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def find_token(symbol: str, chain_id: int) -> Optional[Dict[str, Any]]:
    """Find a token in OpenOcean's token list."""
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
        logger.error(f"Unsupported chain ID: {chain_id}")
        return None
    
    try:
        # Get token list from OpenOcean
        url = f"https://open-api.openocean.finance/v4/{chain}/tokenList"
        logger.info(f"Fetching token list from {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data["code"] == 200 and "data" in data:
                    tokens = data["data"]
                    
                    # Clean up search symbol
                    search_symbol = symbol.strip().lstrip('$').upper()
                    logger.info(f"Searching for token: {search_symbol}")
                    
                    # First try exact match
                    for token in tokens:
                        if token["symbol"].upper() == search_symbol:
                            logger.info(f"Found exact match: {token}")
                            return token
                    
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
                        logger.info(f"Found fuzzy match: {best_match}")
                        return best_match
                    
                    logger.warning(f"No matches found for {symbol}")
                else:
                    logger.error(f"Invalid response format: {data}")
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"Error looking up token: {str(e)}")
    
    return None

async def main():
    # Test with some tokens
    test_tokens = [
        ("$eth", 8453),  # Base chain
        ("$pepe", 1),      # Ethereum
        ("$arb", 42161),   # Arbitrum
        ("$op", 10),       # Optimism
        ("$matic", 137),   # Polygon
    ]
    
    for symbol, chain_id in test_tokens:
        logger.info(f"\nLooking up {symbol} on chain {chain_id}")
        token = await find_token(symbol, chain_id)
        if token:
            print(f"\nFound token {symbol}:")
            print(f"Address: {token['address']}")
            print(f"Name: {token['name']}")
            print(f"Symbol: {token['symbol']}")
            print(f"Decimals: {token['decimals']}")
            if 'usd' in token:
                print(f"Price: ${float(token['usd']):.8f}")
        else:
            print(f"\nToken {symbol} not found on chain {chain_id}")

if __name__ == "__main__":
    asyncio.run(main()) 