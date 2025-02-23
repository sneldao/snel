from typing import Optional
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx
import logging
import sys

# Configure logger to use stdout
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class KyberSwapError(Exception):
    """Base exception for KyberSwap errors"""
    pass

class NoRouteFoundError(KyberSwapError):
    """Raised when no swap route is found"""
    pass

class InsufficientLiquidityError(KyberSwapError):
    """Raised when there's not enough liquidity for the swap"""
    pass

class InvalidTokenError(KyberSwapError):
    """Raised when a token is not supported"""
    pass

class BuildTransactionError(KyberSwapError):
    """Raised when transaction building fails"""
    pass

class KyberQuote(BaseModel):
    router_address: HexAddress
    data: str
    gas: str

async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    chain_id: int,
    recipient: HexAddress,
) -> KyberQuote:
    """Get a swap quote from KyberSwap."""
    try:
        url = f"https://aggregator-api.kyberswap.com/{chain_id}/route/encode"
        
        params = {
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": str(amount),
            "to": recipient,
            "saveGas": "0",
            "gasInclude": "1",
            "slippageTolerance": "50",  # 0.5%
            "clientData": {"source": "pointless"}  # Using double quotes
        }
        
        logger.info(f"Requesting quote from KyberSwap API: {url}")
        logger.info(f"Request params: {params}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:  # Add timeout
            try:
                response = await client.get(url, params=params)
                logger.info(f"KyberSwap API response status: {response.status_code}")
                
                # Try to parse response as JSON
                try:
                    response_data = response.json()
                    logger.info(f"Response data: {response_data}")
                except Exception as json_error:
                    logger.error(f"Failed to parse response as JSON: {response.text}")
                    response_data = {}
                
                if response.status_code == 404:
                    error_msg = response_data.get('message', 'No route found for swap')
                    logger.error(f"No route found: {error_msg}")
                    raise NoRouteFoundError(f"No valid route found: {error_msg}")
                    
                elif response.status_code == 400:
                    error_msg = response_data.get('message', str(response_data))
                    logger.error(f"Bad request: {error_msg}")
                    
                    if "insufficient liquidity" in str(error_msg).lower():
                        raise InsufficientLiquidityError(f"Not enough liquidity: {error_msg}")
                    elif "invalid token" in str(error_msg).lower():
                        raise InvalidTokenError(f"Invalid token: {error_msg}")
                    else:
                        raise BuildTransactionError(f"Failed to build swap: {error_msg}")
                        
                elif response.status_code != 200:
                    error_msg = response_data.get('message', response.text)
                    logger.error(f"Unexpected response: {error_msg}")
                    raise KyberSwapError(f"Unexpected response: {error_msg}")
                
                if "tx" not in response_data:
                    logger.error("Missing transaction data in response")
                    raise BuildTransactionError(f"Missing transaction data in response: {response_data}")
                
                tx_data = response_data["tx"]
                logger.info("Successfully received quote from KyberSwap")
                
                return KyberQuote(
                    router_address=tx_data["to"],
                    data=tx_data["data"],
                    gas=tx_data["gas"]
                )
                
            except httpx.TimeoutException:
                logger.error("Request timed out")
                raise KyberSwapError("Request timed out while getting quote")
                
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise KyberSwapError(f"HTTP error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise KyberSwapError(f"Unexpected error: {str(e)}")

def get_chain_from_chain_id(chain_id: int) -> str:
    """Get chain name from chain ID."""
    chains = {
        1: "ethereum",
        8453: "base",
        42161: "arbitrum",
        10: "optimism",
        137: "polygon",
        43114: "avalanche"
    }
    return chains.get(chain_id, "unknown") 