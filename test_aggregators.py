import asyncio
import logging
import httpx
from typing import Optional, Dict, Any
from web3 import Web3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test parameters
TEST_WALLET = "0x1234567890123456789012345678901234567890"  # Replace with a valid wallet address
CHAIN_ID = 8453  # Base chain
ETH_ADDRESS = "0x0000000000000000000000000000000000000000"  # ETH
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"  # WETH on Base
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
AMOUNT = 0.001  # Small amount for testing

class SimpleSwapTester:
    def __init__(self):
        self.w3 = Web3()
        self.http_client = httpx.AsyncClient(verify=False)  # For development only
        self.zerox_api_key = os.getenv('ZEROX_API_KEY')
        
    async def get_token_decimals(self, token_address: str, chain_id: int) -> int:
        """Get token decimals. Returns 18 for ETH/WETH, otherwise attempts to fetch from contract."""
        if token_address in [ETH_ADDRESS, WETH_ADDRESS]:
            return 18
            
        try:
            # Try QuickNode API first
            quicknode_url = "https://api.quicknode.com/graphql"  # Replace with your QuickNode URL
            query = """
            query($address: String!, $chainId: Int!) {
                token(address: $address, chainId: $chainId) {
                    decimals
                }
            }
            """
            variables = {"address": token_address, "chainId": chain_id}
            
            response = await self.http_client.post(
                quicknode_url,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("token", {}).get("decimals"):
                    return int(data["data"]["token"]["decimals"])
                    
        except Exception as e:
            logger.error(f"Error getting decimals from QuickNode: {str(e)}")
            
        # Default to 18 if we couldn't get the decimals
        return 18
        
    async def convert_to_smallest_units(self, token_address: str, amount: float, chain_id: int) -> int:
        """Convert amount to smallest units based on token decimals."""
        try:
            decimals = await self.get_token_decimals(token_address, chain_id)
            return int(amount * (10 ** decimals))
        except Exception as e:
            logger.error(f"Error converting to smallest units: {str(e)}")
            raise
            
    async def get_0x_quote(self, amount_in_smallest_units: int) -> Dict[str, Any]:
        """Get quote from 0x API using Permit2."""
        logging.info("Testing 0x aggregator...")
        logging.info(f"Amount in smallest units: {amount_in_smallest_units}")
        
        api_key = os.getenv("ZEROX_API_KEY")
        if not api_key:
            logging.error("0x API key not found in environment variables")
            return None
        
        params = {
            "sellToken": WETH_ADDRESS,
            "buyToken": USDC_ADDRESS,
            "sellAmount": str(amount_in_smallest_units),
            "taker": TEST_WALLET,  # Changed from takerAddress to taker
            "chainId": CHAIN_ID
        }
        
        headers = {
            "0x-api-key": api_key,
            "0x-version": "v2"  # Added version header
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.0x.org/swap/permit2/quote",  # Updated to permit2 endpoint
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                quote = response.json()
                logging.info("0x quote received successfully")
                logging.info(f"Quote details: {quote}")
                return quote
        except Exception as e:
            logging.error(f"0x API error: {e.response.text if hasattr(e, 'response') else str(e)}")
            logging.error("0x quote failed")
            return None
            
    async def get_openocean_quote(self, token_in: str, token_out: str, amount_in: int, chain_id: int, taker: str, slippage: float = 1) -> Optional[Dict[str, Any]]:
        """Get quote from OpenOcean API v4."""
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
                logger.error(f"Chain {chain_id} not supported by OpenOcean")
                return None

            base_url = f"https://open-api.openocean.finance/v4/{chain}/swap"
            params = {
                "inTokenAddress": token_in,
                "outTokenAddress": token_out,
                "amount": str(amount_in),
                "gasPrice": "5",
                "slippage": str(slippage),
                "account": taker
            }

            response = await self.http_client.get(base_url, params=params)

            if response.status_code == 200:
                return response.json()
            logger.error(f"OpenOcean API error: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error getting OpenOcean quote: {str(e)}")
            return None
            
    async def get_uniswap_quote(self, amount_in_smallest_units: int) -> Dict[str, Any]:
        """Get quote from Uniswap API."""
        logging.info("Testing uniswap aggregator...")
        logging.info(f"Amount in smallest units: {amount_in_smallest_units}")
        
        api_key = os.getenv("UNISWAP_API_KEY")
        if not api_key:
            logging.error("Uniswap API key not found in environment variables")
            return None
        
        data = {
            "tokenInChainId": CHAIN_ID,
            "tokenIn": WETH_ADDRESS,
            "tokenOutChainId": CHAIN_ID,
            "tokenOut": USDC_ADDRESS,
            "amount": str(amount_in_smallest_units),
            "type": "EXACT_INPUT",
            "configs": [
                {
                    "protocols": ["V2", "V3", "MIXED"],
                    "routingType": "CLASSIC"
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://app.uniswap.org",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.uniswap.org/v2/quote",
                    json=data,
                    headers=headers
                )
                response.raise_for_status()
                quote = response.json()
                logging.info("uniswap quote received successfully")
                logging.info(f"Quote details: {quote}")
                return quote
        except Exception as e:
            logging.error(f"Uniswap API error: {e.response.text if hasattr(e, 'response') else str(e)}")
            logging.error("uniswap quote failed")
            return None
            
    async def get_kyber_quote(self, token_in: str, token_out: str, amount_in: int, chain_id: int, taker: str, slippage: float = 0.5) -> Optional[Dict[str, Any]]:
        """Get quote from Kyber API v1."""
        try:
            # Map chain ID to Kyber chain name
            chain_mapping = {
                1: "ethereum",
                10: "optimism",
                137: "polygon",
                42161: "arbitrum",
                8453: "base",
                534352: "scroll"
            }
            chain = chain_mapping.get(chain_id)
            if not chain:
                logger.error(f"Chain {chain_id} not supported by Kyber")
                return None

            base_url = f"https://aggregator-api.kyberswap.com/{chain}/api/v1/routes"
            params = {
                "tokenIn": WETH_ADDRESS if token_in == ETH_ADDRESS else token_in,
                "tokenOut": token_out,
                "amountIn": str(amount_in)
            }

            response = await self.http_client.get(base_url, params=params)

            if response.status_code == 200:
                return response.json()
            logger.error(f"Kyber API error: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error getting Kyber quote: {str(e)}")
            return None

async def test_aggregator(tester: SimpleSwapTester, aggregator: str):
    """Test a specific aggregator."""
    try:
        # Convert amount to smallest units
        amount_in_smallest_units = await tester.convert_to_smallest_units(
            ETH_ADDRESS, AMOUNT, CHAIN_ID
        )
        
        logger.info(f"Testing {aggregator} aggregator...")
        logger.info(f"Amount in smallest units: {amount_in_smallest_units}")
        
        if aggregator == "0x":
            quote = await tester.get_0x_quote(amount_in_smallest_units)
        elif aggregator == "openocean":
            quote = await tester.get_openocean_quote(
                ETH_ADDRESS, USDC_ADDRESS, amount_in_smallest_units, CHAIN_ID, TEST_WALLET
            )
        elif aggregator == "uniswap":
            quote = await tester.get_uniswap_quote(amount_in_smallest_units)
        elif aggregator == "kyber":
            quote = await tester.get_kyber_quote(
                ETH_ADDRESS, USDC_ADDRESS, amount_in_smallest_units, CHAIN_ID, TEST_WALLET
            )
        
        if quote:
            logger.info(f"{aggregator} quote received successfully")
            logger.info(f"Quote details: {quote}")
            return True
        else:
            logger.error(f"{aggregator} quote failed")
            return False
    except Exception as e:
        logger.error(f"Error testing {aggregator}: {str(e)}")
        return False

async def main():
    # Initialize tester
    tester = SimpleSwapTester()
    
    # List of aggregators to test
    aggregators = ["0x", "openocean", "uniswap", "kyber"]
    
    # Test results
    results = {}
    
    # Test each aggregator
    for aggregator in aggregators:
        success = await test_aggregator(tester, aggregator)
        results[aggregator] = "Working" if success else "Failed"
    
    # Print summary
    logger.info("\nTest Results Summary:")
    for aggregator, status in results.items():
        logger.info(f"{aggregator}: {status}")
    
    # Close the HTTP client
    await tester.http_client.aclose()

if __name__ == "__main__":
    asyncio.run(main()) 