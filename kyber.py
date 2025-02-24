from typing import Optional
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx
import logging
import sys
import json
import time

# Configure logger to use stdout
logger = logging.getLogger(__name__)
# Remove all handlers to prevent duplicates
logger.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger

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

class TransferFromFailedError(KyberSwapError):
    """Raised when the token transfer fails, likely due to insufficient balance or allowance"""
    pass

class KyberQuote(BaseModel):
    router_address: HexAddress
    data: str
    gas: str

def get_chain_name(chain_id: int) -> str:
    """Get chain name from chain ID for Kyber API."""
    chains = {
        1: "ethereum",
        8453: "base",
        42161: "arbitrum",
        10: "optimism",
        137: "polygon",
        43114: "avalanche",
        324: "zksync",
        250: "fantom",
        59144: "linea",
        1101: "polygon-zkevm",
        534352: "scroll",
        5000: "mantle",
        81457: "blast",
        146: "sonic"
    }
    return chains.get(chain_id, "unknown")

async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    chain_id: int,
    recipient: HexAddress,
) -> KyberQuote:
    """Get a swap quote from KyberSwap using APIv1."""
    try:
        chain_name = get_chain_name(chain_id)
        if chain_name == "unknown":
            raise KyberSwapError(f"Unsupported chain ID: {chain_id}")

        # Step 1: Get route using APIv1
        route_url = f"https://aggregator-api.kyberswap.com/{chain_name}/api/v1/routes"
        
        route_params = {
            "tokenIn": token_in,
            "tokenOut": token_out,
            "amountIn": str(amount),
            "saveGas": "0",
            "gasInclude": "1"
        }
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "pointless/1.0",
            "x-client-id": "pointless"  # Identify our client
        }
        
        logger.info(f"Requesting route from KyberSwap API: {route_url}")
        logger.info(f"Route params: {route_params}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                route_response = await client.get(route_url, params=route_params, headers=headers)
                logger.info(f"KyberSwap route API response status: {route_response.status_code}")
                
                try:
                    route_data = route_response.json()
                    logger.info(f"Route response data: {route_data}")
                except Exception as json_error:
                    logger.error(f"Failed to parse route response as JSON: {route_response.text}")
                    raise KyberSwapError("Failed to parse route response")
                
                if route_response.status_code != 200:
                    error_msg = route_data.get('message', route_response.text)
                    logger.error(f"Route request failed: {error_msg}")
                    if route_response.status_code == 404:
                        raise NoRouteFoundError("No valid route found for this swap")
                    raise KyberSwapError(f"Route request failed: {error_msg}")
                
                if not route_data.get('data', {}).get('routeSummary'):
                    logger.error("No route summary in response")
                    raise NoRouteFoundError("No valid route found for this swap")
                
                # Step 2: Build transaction using the route
                build_url = f"https://aggregator-api.kyberswap.com/{chain_name}/api/v1/route/build"
                
                build_data = {
                    "routeSummary": route_data['data']['routeSummary'],
                    "sender": recipient,  # Use recipient as sender
                    "recipient": recipient,
                    "slippageTolerance": 50,  # 0.5% slippage tolerance
                    "deadline": int(time.time()) + 1200,  # 20 minutes
                    "source": "pointless",
                    "enableGasEstimation": True
                }
                
                logger.info(f"Building transaction at: {build_url}")
                build_response = await client.post(build_url, json=build_data, headers=headers)
                logger.info(f"Build API response status: {build_response.status_code}")
                
                try:
                    build_data = build_response.json()
                    logger.info(f"Build response data: {build_data}")
                except Exception as json_error:
                    logger.error(f"Failed to parse build response as JSON: {build_response.text}")
                    raise BuildTransactionError("Failed to parse build response")
                
                if build_response.status_code != 200:
                    error_msg = build_data.get('message', build_response.text)
                    logger.error(f"Build request failed: {error_msg}")
                    
                    # Check for specific error messages
                    if "TRANSFER_FROM_FAILED" in error_msg:
                        raise TransferFromFailedError(
                            "Token transfer failed. Please ensure you have sufficient balance and have approved the router."
                        )
                    elif "No valid route found" in error_msg:
                        raise NoRouteFoundError("No valid route found for this swap")
                    elif "insufficient liquidity" in error_msg.lower():
                        raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                    elif "invalid token" in error_msg.lower():
                        raise InvalidTokenError("One or more tokens are invalid or not supported")
                    
                    raise BuildTransactionError(f"Failed to build transaction: {error_msg}")
                
                tx_data = build_data['data']
                logger.info("Successfully built transaction")
                
                return KyberQuote(
                    router_address=tx_data["routerAddress"],
                    data=tx_data["data"],
                    gas=tx_data.get("gas", "500000")  # Default gas if not provided
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
    return get_chain_name(chain_id) 