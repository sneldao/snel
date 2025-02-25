import asyncio
import os
import logging
from dotenv import load_dotenv
from app.services.token_service import TokenService

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set environment variable to disable SSL verification for testing
os.environ["DISABLE_SSL_VERIFY"] = "true"

async def test_quicknode_lookup():
    """Test the QuickNode token lookup functionality."""
    token_service = TokenService()
    
    # Test tokens on different chains
    test_cases = [
        # (token_symbol, chain_id, expected_result)
        ("ETH", 1, True),  # Ethereum on Ethereum
        ("USDC", 1, True),  # USDC on Ethereum
        ("OP", 10, True),   # OP on Optimism
        ("ARB", 42161, True),  # ARB on Arbitrum
        ("MATIC", 137, True),  # MATIC on Polygon
        ("NURI", 534352, True),  # NURI on Scroll
        ("NONEXISTENT", 1, False),  # Non-existent token
    ]
    
    for symbol, chain_id, expected_success in test_cases:
        logger.info(f"Testing lookup for {symbol} on chain {chain_id}")
        result = await token_service._lookup_token_quicknode(symbol, chain_id)
        
        if expected_success:
            if result[0]:
                logger.info(f"✅ Successfully found {symbol} on chain {chain_id}: {result}")
            else:
                logger.error(f"❌ Failed to find {symbol} on chain {chain_id}")
        else:
            if not result[0]:
                logger.info(f"✅ Correctly did not find non-existent token {symbol}")
            else:
                logger.warning(f"⚠️ Unexpectedly found token for {symbol}: {result}")
    
    # Test contract address lookup
    eth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH on Ethereum
    logger.info(f"Testing metadata lookup for contract {eth_address} on chain 1")
    metadata = await token_service._get_token_metadata_by_address_quicknode(eth_address, 1)
    if metadata:
        logger.info(f"✅ Successfully got metadata for {eth_address}: {metadata}")
    else:
        logger.error(f"❌ Failed to get metadata for {eth_address}")

async def main():
    """Run the test."""
    logger.info("Starting QuickNode integration test")
    await test_quicknode_lookup()
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main()) 