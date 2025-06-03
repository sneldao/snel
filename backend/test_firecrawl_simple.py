import os
import asyncio
import json
import httpx
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    logger.error("FIRECRAWL_API_KEY not found in environment variables")
    exit(1)

async def test_search_endpoint(query: str):
    """Test the search endpoint with a given query."""
    url = f"https://api.firecrawl.dev/search?q={query}"
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"Testing search endpoint with query: {query}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
            logger.info(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Success! Response structure:")
                print(json.dumps(data, indent=2))
                return data
            else:
                logger.error(f"Error: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        return None

async def main():
    """Test Firecrawl API with a single query."""
    protocol = input("Enter a protocol name to search (e.g., Uniswap, Aave): ").strip()
    if not protocol:
        protocol = "Uniswap"
        logger.info(f"Using default protocol: {protocol}")
    
    await test_search_endpoint(protocol)

if __name__ == "__main__":
    logger.info("Starting Firecrawl API test")
    asyncio.run(main())
    logger.info("Completed Firecrawl API test")