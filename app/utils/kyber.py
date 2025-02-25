from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx
import logging
import sys
import json
import time
import os

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

KYBER_API_URL = "https://aggregator-api.kyberswap.com"

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
            "x-client-id": "pointless"
        }
        
        logger.info(f"Requesting route from KyberSwap API: {route_url}")
        logger.info(f"Route params: {route_params}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                "sender": recipient,
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
                
                # Check for TRANSFER_FROM_FAILED in the error message or code
                if (
                    "TRANSFER_FROM_FAILED" in error_msg or 
                    build_data.get('code') == 4227 or  # Add specific error code check
                    "TransferHelper: TRANSFER_FROM_FAILED" in error_msg
                ):
                    logger.info("Transfer failed, needs approval")
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
    except Exception as e:
        logger.error(f"Error in get_quote: {str(e)}")
        raise

def get_chain_from_chain_id(chain_id: int) -> str:
    """Get chain name from chain ID."""
    return get_chain_name(chain_id)

def get_kyber_quote(
    chain_id: int,
    token_in: str,
    token_out: str,
    amount_in: str,
    slippage_tolerance: int = 50,  # 0.5%
) -> Dict[str, Any]:
    """
    Get a quote from Kyber for a token swap.
    
    Args:
        chain_id: The chain ID (1 for Ethereum, 137 for Polygon, etc.)
        token_in: The address of the token to swap from
        token_out: The address of the token to swap to
        amount_in: The amount of token_in to swap (in wei)
        slippage_tolerance: The slippage tolerance in basis points (1 = 0.01%)
        
    Returns:
        A dictionary containing the quote data
    """
    logger.info(f"Getting Kyber quote for {token_in} -> {token_out}, amount: {amount_in}")
    
    url = f"{KYBER_API_URL}/api/v1/routes"
    
    params = {
        "tokenIn": token_in,
        "tokenOut": token_out,
        "amountIn": amount_in,
        "saveGas": "false",
        "gasInclude": "true",
        "slippageTolerance": slippage_tolerance,
        "clientData": json.dumps({
            "source": "Dowse Pointless",
        }),
        "chargeFeeBy": "currency_in",
        "feeAmount": "0",
        "isInBps": "false",
        "excludeDexes": "",
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "chainId": str(chain_id),
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("data") or not data["data"].get("routeSummary"):
                logger.error(f"Invalid Kyber response: {data}")
                raise ValueError("Invalid Kyber response")
                
            return data
    except Exception as e:
        logger.error(f"Error getting Kyber quote: {e}")
        raise

def build_kyber_transaction(
    chain_id: int,
    token_in: str,
    token_out: str,
    amount_in: str,
    slippage_tolerance: int = 50,  # 0.5%
    sender_address: Optional[str] = None,
    recipient_address: Optional[str] = None,
    deadline: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a transaction for a token swap using Kyber.
    
    Args:
        chain_id: The chain ID (1 for Ethereum, 137 for Polygon, etc.)
        token_in: The address of the token to swap from
        token_out: The address of the token to swap to
        amount_in: The amount of token_in to swap (in wei)
        slippage_tolerance: The slippage tolerance in basis points (1 = 0.01%)
        sender_address: The address of the sender (optional)
        recipient_address: The address of the recipient (optional)
        deadline: The deadline for the transaction (optional)
        
    Returns:
        A dictionary containing the transaction data
    """
    logger.info(f"Building Kyber transaction for {token_in} -> {token_out}, amount: {amount_in}")
    
    url = f"{KYBER_API_URL}/api/v1/route/build"
    
    body = {
        "routeSummary": get_kyber_quote(
            chain_id, token_in, token_out, amount_in, slippage_tolerance
        )["data"]["routeSummary"],
        "slippageTolerance": slippage_tolerance,
    }
    
    if sender_address:
        body["sender"] = sender_address
        
    if recipient_address:
        body["recipient"] = recipient_address
        
    if deadline:
        body["deadline"] = deadline
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                json=body,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "chainId": str(chain_id),
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("data") or not data["data"].get("data"):
                logger.error(f"Invalid Kyber build response: {data}")
                raise ValueError("Invalid Kyber build response")
                
            return data["data"]
    except Exception as e:
        logger.error(f"Error building Kyber transaction: {e}")
        raise 