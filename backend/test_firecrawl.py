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

async def test_scrape_endpoint(protocol_name: str):
    """Test the scrape endpoint with a given protocol name."""
    url = f"https://api.firecrawl.dev/scrape/protocol/{protocol_name}"
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"Testing scrape endpoint with protocol: {protocol_name}")
    
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

async def test_scrape_url_endpoint(url_to_scrape: str):
    """Test the scrape URL endpoint with a given URL."""
    url = "https://api.firecrawl.dev/scrape/url"
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": url_to_scrape
    }
    
    logger.info(f"Testing scrape URL endpoint with URL: {url_to_scrape}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
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

async def test_all_endpoints():
    """Test all Firecrawl endpoints with different inputs."""
    # Test search endpoint with different queries
    searches = [
        "Uniswap",
        "Aave protocol",
        "DeFi lending protocols",
        "Top DeFi protocols by TVL"
    ]
    
    for query in searches:
        logger.info(f"\n{'='*50}\nTesting search for: {query}\n{'='*50}")
        await test_search_endpoint(query)
    
    # Test scrape protocol endpoint with different protocols
    protocols = [
        "Uniswap",
        "Aave",
        "Compound",
        "MakerDAO"
    ]
    
    for protocol in protocols:
        logger.info(f"\n{'='*50}\nTesting protocol scrape for: {protocol}\n{'='*50}")
        await test_scrape_endpoint(protocol)
    
    # Test scrape URL endpoint with different URLs
    urls = [
        "https://uniswap.org",
        "https://aave.com",
        "https://compound.finance",
        "https://makerdao.com"
    ]
    
    for url in urls:
        logger.info(f"\n{'='*50}\nTesting URL scrape for: {url}\n{'='*50}")
        await test_scrape_url_endpoint(url)

if __name__ == "__main__":
    logger.info("Starting Firecrawl API tests")
    asyncio.run(test_all_endpoints())
    logger.info("Completed Firecrawl API tests")