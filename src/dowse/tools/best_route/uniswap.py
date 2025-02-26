import os
from typing import Literal, Optional, Dict, Any, List
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
    aggregator: str = "uniswap"


class UniswapError(Exception):
    """Base exception for Uniswap API errors"""
    pass


class NoRouteFoundError(UniswapError):
    """Raised when no swap route is found"""
    pass


class InsufficientLiquidityError(UniswapError):
    """Raised when there's insufficient liquidity for the swap"""
    pass


class InvalidTokenError(UniswapError):
    """Raised when token is not supported or invalid"""
    pass


class BuildTransactionError(UniswapError):
    """Raised when transaction building fails"""
    pass


# Universal Router addresses by chain
UNIVERSAL_ROUTER_ADDRESSES = {
    1: "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",  # Ethereum Mainnet
    10: "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",  # Optimism
    137: "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",  # Polygon
    42161: "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",  # Arbitrum
    8453: "0x198EF79F1F515F02dFE9e3115eD9fC07183f02fC",  # Base
    534352: "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",  # Scroll (assuming same as others)
}


def get_chain_from_chain_id(chain_id: int) -> str:
    """Convert chain ID to chain name for Uniswap API."""
    chain_mapping = {
        1: "ethereum",
        10: "optimism",
        137: "polygon",
        42161: "arbitrum",
        8453: "base",
        534352: "scroll",
    }
    return chain_mapping.get(chain_id, "ethereum")


def get_router_address(chain_id: int) -> str:
    """Get the Universal Router address for a specific chain."""
    return UNIVERSAL_ROUTER_ADDRESSES.get(chain_id, UNIVERSAL_ROUTER_ADDRESSES[1])


async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: float,
    chain_id: int,
    recipient: HexAddress,
    slippage_percentage: float = 1.0,
    is_exact_output: bool = False,
) -> Quote:
    """
    Get a swap quote from Uniswap API.
    
    Args:
        token_in: Address of the token to sell
        token_out: Address of the token to buy
        amount: Amount of token_in to sell (or token_out to buy if is_exact_output=True)
        chain_id: Chain ID
        recipient: Address that will receive the bought tokens
        slippage_percentage: Maximum acceptable slippage in percentage
        is_exact_output: If True, amount is the amount of token_out to buy
    
    Returns:
        Quote object with transaction details
    """
    try:
        # Get the appropriate chain name for the API
        chain_name = get_chain_from_chain_id(chain_id)
        
        # Determine if we're dealing with native tokens
        is_native_in = token_in.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        is_native_out = token_out.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        
        # For native tokens, use the appropriate address
        if is_native_in:
            # Use ETH for native token
            token_in = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            logger.info(f"Using ETH address for native token: {token_in}")
        
        if is_native_out:
            # Use ETH for native token
            token_out = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            logger.info(f"Using ETH address for native token: {token_out}")
        
        # Determine if we're using exactInput or exactOutput
        exact_type = "exactOutput" if is_exact_output else "exactInput"
        
        # Convert amount to smallest unit (assuming 18 decimals for now)
        # In a production environment, you'd want to fetch the actual decimals for each token
        decimals = 18
        amount_in_smallest_unit = int(amount * 10**decimals)
        logger.info(f"Converting amount {amount} to smallest unit with {decimals} decimals: {amount_in_smallest_unit}")
        
        # Prepare API URL
        api_key = os.environ.get("UNISWAP_API_KEY", "")
        base_url = "https://api.uniswap.org/v1/quote"
        
        # Prepare query parameters
        params = {
            "tokenInAddress": token_in,
            "tokenInChainId": chain_id,
            "tokenOutAddress": token_out,
            "tokenOutChainId": chain_id,
            "amount": str(amount_in_smallest_unit),
            "type": exact_type,
            "recipient": recipient,
            "slippageTolerance": slippage_percentage / 100,  # Convert to decimal (1% -> 0.01)
            "protocols": "v2,v3,mixed",
        }
        
        logger.info(f"Uniswap API params: {params}")
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if api_key:
            headers["X-API-KEY"] = api_key
        
        # Make the API request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params, headers=headers)
            
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('errorCode', response.text)
                    logger.error(f"Uniswap API request failed: {error_msg}")
                    
                    if "INSUFFICIENT_LIQUIDITY" in error_msg:
                        raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                    elif "NO_ROUTE" in error_msg:
                        raise NoRouteFoundError("No valid route found for this swap")
                    elif "INVALID_TOKEN" in error_msg:
                        raise InvalidTokenError(f"Invalid token: {error_msg}")
                    
                    raise UniswapError(f"Quote request failed: {error_msg}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse response as JSON: {response.text}")
                    raise UniswapError(f"Quote request failed with status {response.status_code}")
            
            try:
                quote_data = response.json()
                logger.info(f"Uniswap API response: {quote_data}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse response as JSON: {response.text}")
                raise UniswapError("Failed to parse quote response")
            
            # Extract the necessary data for the transaction
            router_address = get_router_address(chain_id)
            
            # Extract transaction data
            to_address = quote_data.get("methodParameters", {}).get("to", router_address)
            data = quote_data.get("methodParameters", {}).get("calldata")
            value = quote_data.get("methodParameters", {}).get("value", "0")
            gas = quote_data.get("methodParameters", {}).get("gasLimit", "500000")
            
            # Extract token amounts
            token_in_amount = quote_data.get("quote", {}).get("amount")
            token_out_amount = quote_data.get("quote", {}).get("amount")
            
            if is_exact_output:
                token_in_amount = quote_data.get("quote", {}).get("amount")
                token_out_amount = str(amount_in_smallest_unit)
            else:
                token_in_amount = str(amount_in_smallest_unit)
                token_out_amount = quote_data.get("quote", {}).get("amount")
            
            # Ensure data has 0x prefix
            if data and not data.startswith("0x"):
                data = "0x" + data
                logger.info(f"Added 0x prefix to data: {data}")
            
            # Ensure value has 0x prefix for hex values
            if value and not str(value).startswith("0x") and int(value) > 0:
                value = f"0x{int(value):x}"
                logger.info(f"Converted value to hex: {value}")
            
            # Create and return the quote object
            return Quote(
                tokenIn=token_in,
                tokenOut=token_out,
                amountIn=int(token_in_amount),
                amountOut=int(token_out_amount),
                gas=int(gas),
                data=data,
                routerAddress=to_address,
                transactionValue=value,
                aggregator="uniswap"
            )
    except Exception as e:
        logger.error(f"Error in get_quote: {str(e)}")
        raise 