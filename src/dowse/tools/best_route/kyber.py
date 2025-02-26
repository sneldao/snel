import os
from typing import Literal
import json
import time

import httpx
from eth_typing import HexAddress, HexStr
from pydantic import BaseModel, Field

from dowse.logger import logger


class RouteSummary(BaseModel):
    tokenIn: str
    tokenOut: str
    amountIn: str
    amountOut: str
    gas: str
    gasUsd: str
    gasPrice: str
    route: list


class Quote(BaseModel):
    token_in: HexAddress = Field(alias="tokenIn")
    token_out: HexAddress = Field(alias="tokenOut")
    amount_in: int = Field(alias="amountIn")
    amount_out: int = Field(alias="amountOut")
    gas: int
    data: str  # The encoded swap data
    router_address: str = Field(alias="routerAddress")
    transaction_value: str = Field(default="0", alias="transactionValue")
    aggregator: str = "kyber"


class KyberSwapError(Exception):
    """Base exception for KyberSwap API errors"""
    pass

class NoRouteFoundError(KyberSwapError):
    """Raised when no swap route is found"""
    pass

class InsufficientLiquidityError(KyberSwapError):
    """Raised when there's insufficient liquidity for the swap"""
    pass

class InvalidTokenError(KyberSwapError):
    """Raised when token is not supported or invalid"""
    pass

class BuildTransactionError(KyberSwapError):
    """Raised when transaction building fails"""
    pass

async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    chain_id: Literal[1, 8453, 42161, 10, 137, 43114] = 8453,
    recipient: HexAddress = None,
) -> Quote:
    chain = get_chain_from_chain_id(chain_id)
    
    # Format addresses to checksum format
    token_in_addr = token_in.lower()
    token_out_addr = token_out.lower()
    recipient_addr = recipient.lower() if recipient else token_in_addr
    
    base_url = "https://aggregator-api.kyberswap.com"
    path = f"{chain}/api/v1/routes"
    
    # Build URL with properly formatted parameters
    url = f"{base_url}/{path}"
    params = {
        "tokenIn": token_in_addr,
        "tokenOut": token_out_addr,
        "amountIn": str(amount),  # Convert to string to avoid scientific notation
    }
    
    logger.info(f"Getting Kyber quote: {url} with params: {params}")
    
    tries = 0
    while tries < 3:
        tries += 1
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Get route
                response = await client.get(url, params=params)
                response_json = response.json()
                
                # Handle error responses with specific error types
                if response.status_code == 400:
                    error_msg = response_json.get("message", "")
                    if "insufficient liquidity" in error_msg.lower():
                        raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                    elif "invalid token" in error_msg.lower():
                        raise InvalidTokenError(f"Invalid or unsupported token(s): {error_msg}")
                    elif "no route" in error_msg.lower():
                        raise NoRouteFoundError("No valid route found for this swap")
                    else:
                        raise KyberSwapError(f"Invalid request: {error_msg}")
                elif response.status_code != 200:
                    raise KyberSwapError(f"API error: {response.status_code} - {response.text}")
                
                if not response_json or "data" not in response_json:
                    raise KyberSwapError("Invalid API response format")
                
                data = response_json["data"]
                if not data:
                    raise NoRouteFoundError("No routes available for this swap")
                if "routeSummary" not in data:
                    raise KyberSwapError("Missing route summary in response")
                
                route_summary = data["routeSummary"]
                router_address = data.get("routerAddress")
                if not router_address:
                    raise BuildTransactionError("Missing router address in response")
                
                # Step 2: Build transaction data
                build_url = f"{base_url}/{chain}/api/v1/route/build"
                current_time = int(time.time())
                deadline = current_time + 1800  # 30 minutes from now
                
                build_request = {
                    "routeSummary": route_summary,
                    "slippageTolerance": 50,  # 0.5% in bips
                    "deadline": deadline,
                    "sender": recipient_addr,
                    "recipient": recipient_addr,
                    "source": "dowse"
                }
                
                logger.info(f"Building swap with recipient: {recipient_addr}")
                
                build_response = await client.post(
                    build_url,
                    json=build_request
                )
                
                build_data = build_response.json()
                logger.info(f"Build response: {json.dumps(build_data, indent=2)}")
                
                # Detailed validation of build response
                if not build_data:
                    raise BuildTransactionError("Empty response from build endpoint")
                if "data" not in build_data:
                    raise BuildTransactionError("Missing data in build response")
                
                tx_data = build_data.get("data", {})
                if not isinstance(tx_data, dict):
                    raise BuildTransactionError(f"Invalid tx_data format: {tx_data}")
                
                # Extract encoded data - handle both possible response formats
                encoded_data = None
                if "encodedData" in tx_data:
                    encoded_data = tx_data["encodedData"]
                elif "tx" in tx_data and isinstance(tx_data["tx"], dict):
                    encoded_data = tx_data["tx"].get("data")
                elif "data" in tx_data:
                    encoded_data = tx_data["data"]
                
                if not encoded_data:
                    logger.error(f"Response structure: {json.dumps(build_data, indent=2)}")
                    raise BuildTransactionError(f"Could not find transaction data in response")
                
                # Extract transaction value for native token swaps
                transaction_value = "0"
                if "transactionValue" in build_data.get("data", {}):
                    transaction_value = build_data["data"]["transactionValue"]
                elif "tx" in tx_data and isinstance(tx_data["tx"], dict):
                    transaction_value = tx_data["tx"].get("value", "0")
                
                logger.info(f"Transaction value for swap: {transaction_value}")
                
                return Quote(
                    tokenIn=route_summary["tokenIn"],
                    tokenOut=route_summary["tokenOut"],
                    amountIn=int(route_summary["amountIn"]),
                    amountOut=int(route_summary["amountOut"]),
                    gas=int(route_summary["gas"]),
                    data=encoded_data,
                    routerAddress=router_address,
                    transactionValue=transaction_value
                )
                
        except (NoRouteFoundError, InsufficientLiquidityError, InvalidTokenError) as e:
            # Don't retry for these specific errors as they won't change
            logger.error("Permanent error getting quote: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error getting quote (attempt %d/3): %s", tries, str(e))
            if tries == 3:
                if isinstance(e, KyberSwapError):
                    raise
                raise KyberSwapError(f"Failed to get quote after 3 attempts: {str(e)}")
            continue

    raise KyberSwapError("Failed to get quote after multiple retries")


def get_chain_from_chain_id(
    chain_id: Literal[1, 8453, 42161, 10, 137, 43114],
) -> Literal["ethereum", "base", "arbitrum", "optimism", "polygon", "avalanche"]:
    mapping: dict[
        int,
        Literal["ethereum", "base", "arbitrum", "optimism", "polygon", "avalanche"],
    ] = {
        8453: "base",
        42161: "arbitrum",
        10: "optimism",
        137: "polygon",
        43114: "avalanche",
        1: "ethereum",
    }
    return mapping[chain_id]
