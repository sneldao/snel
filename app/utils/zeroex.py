from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx
import logging
import sys
import json
import time
import os
from app.config.chains import get_native_token_address, is_native_token
from web3 import Web3
from fastapi import HTTPException

# Configure logger to use stdout
logger = logging.getLogger(__name__)
# Remove all handlers to prevent duplicates
logger.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger

# Check if SSL verification should be disabled (for development only)
DISABLE_SSL_VERIFY = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"
if DISABLE_SSL_VERIFY and not os.environ.get("SSL_WARNING_SHOWN"):
    logger.warning("⚠️ SECURITY WARNING: SSL certificate verification is disabled. This makes your connections less secure and should ONLY be used during development.")
    # Mark that we've shown the warning
    os.environ["SSL_WARNING_SHOWN"] = "true"

class ZeroExError(Exception):
    """Base exception for 0x API errors"""
    pass

class NoRouteFoundError(ZeroExError):
    """Raised when no swap route is found"""
    pass

class InsufficientLiquidityError(ZeroExError):
    """Raised when there's not enough liquidity for the swap"""
    pass

class InvalidTokenError(ZeroExError):
    """Raised when a token is not supported"""
    pass

class BuildTransactionError(ZeroExError):
    """Raised when transaction building fails"""
    pass

class ZeroExQuote(BaseModel):
    """Model for 0x API quote response"""
    to: HexAddress
    data: str
    value: Optional[str] = None
    gas: str
    gas_price: Optional[str] = None
    protocol_fee: Optional[str] = None
    buy_token_address: HexAddress
    sell_token_address: HexAddress
    buy_amount: str
    sell_amount: str
    allowance_target: Optional[HexAddress] = None

# 0x API base URL
ZEROEX_API_URL = "https://api.0x.org"

# 0x API key - should be set in environment variables
ZEROEX_API_KEY = os.environ.get("ZEROEX_API_KEY", "")

# Chain ID to network name mapping for 0x API
def get_chain_endpoint(chain_id: int) -> str:
    """Get the appropriate 0x API endpoint for the given chain ID."""
    chains = {
        1: "",  # Mainnet (empty string, uses base URL)
        8453: "/base",  # Base
        42161: "/arbitrum",  # Arbitrum
        10: "/optimism",  # Optimism
        137: "/polygon",  # Polygon
        43114: "/avalanche",  # Avalanche
        56: "/bsc",  # Binance Smart Chain
        250: "/fantom",  # Fantom
        100: "/gnosis",  # Gnosis Chain
    }
    
    if chain_id not in chains:
        logger.warning(f"Chain ID {chain_id} not explicitly supported by 0x API, defaulting to mainnet")
        return ""
    
    return chains[chain_id]

async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: float,
    chain_id: int,
    recipient: HexAddress,
    is_exact_output: bool = False,
    slippage_percentage: float = 1.0,  # 1% slippage by default
) -> ZeroExQuote:
    """
    Get a swap quote from 0x API.
    
    Args:
        token_in: Address of the token to sell
        token_out: Address of the token to buy
        amount: Amount of token_in to sell (or token_out to buy if is_exact_output=True)
        chain_id: Chain ID
        recipient: Address that will receive the bought tokens
        is_exact_output: If True, amount is the amount of token_out to buy
        slippage_percentage: Maximum acceptable slippage in percentage
    
    Returns:
        ZeroExQuote object with transaction details
    """
    try:
        # Get the appropriate endpoint for the chain
        chain_endpoint = get_chain_endpoint(chain_id)
        
        # Check if we have an API key
        if not ZEROEX_API_KEY:
            logger.warning("No 0x API key provided. Using public API with rate limits.")
        
        # Determine if we're dealing with a native token (ETH)
        is_native_in = is_native_token(token_in.lower())
        is_native_out = is_native_token(token_out.lower())
        
        logger.info(f"Token {token_in} is native: {is_native_in}")
        logger.info(f"Token {token_out} is native: {is_native_out}")
        
        # For native tokens, use the appropriate address
        if is_native_in:
            # Special handling for Base chain (8453)
            if chain_id == 8453:
                # For Base chain, use the WETH address directly
                token_in = "0x4200000000000000000000000000000000000006"
                logger.info(f"Using Base chain WETH address for native token: {token_in}")
            else:
                # For other chains, use the generic ETH address
                token_in = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                logger.info(f"Using ETH address for native token: {token_in}")
        
        if is_native_out:
            # Special handling for Base chain (8453)
            if chain_id == 8453:
                # For Base chain, use the WETH address directly
                token_out = "0x4200000000000000000000000000000000000006"
                logger.info(f"Using Base chain WETH address for native token: {token_out}")
            else:
                # For other chains, use the generic ETH address
                token_out = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                logger.info(f"Using ETH address for native token: {token_out}")
        
        # Determine if we're using sellAmount or buyAmount
        amount_param_name = "buyAmount" if is_exact_output else "sellAmount"
        
        # Convert amount to smallest unit (assuming 18 decimals for now)
        # In a production environment, you'd want to fetch the actual decimals for each token
        decimals = 18
        amount_in_smallest_unit = int(amount * 10**decimals)
        logger.info(f"Converting amount {amount} to smallest unit with {decimals} decimals: {amount_in_smallest_unit}")
        
        # Prepare query parameters
        params = {
            "sellToken": token_in,
            "buyToken": token_out,
            amount_param_name: str(amount_in_smallest_unit),
            "takerAddress": recipient,
            "slippagePercentage": str(slippage_percentage / 100),  # Convert to decimal (1% -> 0.01)
        }
        
        logger.info(f"0x API params: {params}")
        
        # Prepare headers
        headers = {
            "0x-api-key": ZEROEX_API_KEY,
            "0x-version": "v2",
        }
        
        # First, get a price quote to check if the swap is possible
        price_url = f"{ZEROEX_API_URL}{chain_endpoint}/swap/v1/price"
        logger.info(f"Getting price from 0x API: {price_url}")
        
        async with httpx.AsyncClient(timeout=30.0, verify=not DISABLE_SSL_VERIFY) as client:
            price_response = await client.get(price_url, params=params, headers=headers)
            
            if price_response.status_code != 200:
                try:
                    error_data = price_response.json()
                    error_msg = error_data.get('reason', price_response.text)
                    logger.error(f"0x API price request failed: {error_msg}")
                    
                    if "insufficient liquidity" in error_msg.lower():
                        raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                    elif "no routes found" in error_msg.lower():
                        raise NoRouteFoundError("No valid route found for this swap")
                    
                    raise ZeroExError(f"Price request failed: {error_msg}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse price response as JSON: {price_response.text}")
                    raise ZeroExError(f"Price request failed with status {price_response.status_code}")
            
            try:
                price_data = price_response.json()
                logger.info(f"0x API price response: {price_data}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse price response as JSON: {price_response.text}")
                raise ZeroExError("Failed to parse price response")
            
            # Now get the actual quote for the transaction
            quote_url = f"{ZEROEX_API_URL}{chain_endpoint}/swap/v1/quote"
            logger.info(f"Getting quote from 0x API: {quote_url}")
            
            quote_response = await client.get(quote_url, params=params, headers=headers)
            
            if quote_response.status_code != 200:
                try:
                    error_data = quote_response.json()
                    error_msg = error_data.get('reason', quote_response.text)
                    logger.error(f"0x API quote request failed: {error_msg}")
                    
                    if "insufficient liquidity" in error_msg.lower():
                        raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                    elif "no routes found" in error_msg.lower():
                        raise NoRouteFoundError("No valid route found for this swap")
                    
                    raise ZeroExError(f"Quote request failed: {error_msg}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse quote response as JSON: {quote_response.text}")
                    raise ZeroExError(f"Quote request failed with status {quote_response.status_code}")
            
            try:
                quote_data = quote_response.json()
                logger.info(f"0x API quote response: {quote_data}")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse quote response as JSON: {quote_response.text}")
                raise ZeroExError("Failed to parse quote response")
            
            # Extract the necessary data for the transaction
            to_address = quote_data.get("to")
            data = quote_data.get("data")
            value = quote_data.get("value", "0")
            gas = quote_data.get("gas", "500000")  # Default to 500,000 gas if not provided
            gas_price = quote_data.get("gasPrice")
            protocol_fee = quote_data.get("protocolFee", "0")
            buy_token_address = quote_data.get("buyTokenAddress")
            sell_token_address = quote_data.get("sellTokenAddress")
            buy_amount = quote_data.get("buyAmount")
            sell_amount = quote_data.get("sellAmount")
            allowance_target = quote_data.get("allowanceTarget")
            
            # Ensure data has 0x prefix
            if data and not data.startswith("0x"):
                data = "0x" + data
                logger.info(f"Added 0x prefix to data: {data}")
            
            # Ensure value has 0x prefix for hex values
            if value and not str(value).startswith("0x") and int(value) > 0:
                value = f"0x{int(value):x}"
                logger.info(f"Converted value to hex: {value}")
            
            # Process value field for the response
            value_for_response = None
            if value:
                if value.startswith("0x"):
                    if int(value, 16) > 0:
                        value_for_response = value
                else:
                    if int(value) > 0:
                        value_for_response = value
            
            # Create and return the quote object
            return ZeroExQuote(
                to=to_address,
                data=data,
                value=value_for_response,
                gas=gas,
                gas_price=gas_price,
                protocol_fee=protocol_fee,
                buy_token_address=buy_token_address,
                sell_token_address=sell_token_address,
                buy_amount=buy_amount,
                sell_amount=sell_amount,
                allowance_target=allowance_target
            )
    except Exception as e:
        logger.error(f"Error in get_quote: {str(e)}")
        raise 