import logging
import aiohttp
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from app.config.chains import get_chain_config, get_wrapped_native_token_address
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)

# Initialize TokenService
token_service = TokenService()

async def get_quote(
    token_in: str,
    token_out: str,
    amount: float,
    chain_id: int,
    slippage: float = 1.0,
    is_target_amount: bool = False,
    token_in_decimals: Optional[int] = None,
    token_out_decimals: Optional[int] = None,
    is_native_in: Optional[bool] = None,
    is_wrapped_native_in: Optional[bool] = None,
    is_native_out: Optional[bool] = None,
    is_wrapped_native_out: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Get a quote from 1inch.
    
    Args:
        token_in: Input token address
        token_out: Output token address
        amount: Amount to swap
        chain_id: Chain ID
        slippage: Slippage tolerance in percentage
        is_target_amount: Whether the amount is the target amount (output amount)
        token_in_decimals: Decimals for input token (optional)
        token_out_decimals: Decimals for output token (optional)
        is_native_in: Whether input token is native (optional)
        is_wrapped_native_in: Whether input token is wrapped native (optional)
        is_native_out: Whether output token is native (optional)
        is_wrapped_native_out: Whether output token is wrapped native (optional)
    
    Returns:
        Quote data
    """
    # Check if chain is supported
    chain_config = get_chain_config(chain_id)
    if not chain_config:
        return {"error": f"Chain {chain_id} not supported"}
    
    # 1inch doesn't support target amount quotes directly
    if is_target_amount:
        return {"error": "1inch doesn't support target amount quotes"}
    
    # Determine if tokens are native or wrapped if not provided
    if is_native_in is None:
        is_native_in = token_service.is_native_token(token_in, chain_id)
    
    if is_wrapped_native_in is None:
        is_wrapped_native_in = token_service.is_wrapped_native_token(token_in, chain_id)
    
    if is_native_out is None:
        is_native_out = token_service.is_native_token(token_out, chain_id)
    
    if is_wrapped_native_out is None:
        is_wrapped_native_out = token_service.is_wrapped_native_token(token_out, chain_id)
    
    # Get token decimals if not provided
    if token_in_decimals is None:
        token_in_decimals = token_service.get_token_decimals(token_address=token_in, chain_id=chain_id)
    
    if token_out_decimals is None:
        token_out_decimals = token_service.get_token_decimals(token_address=token_out, chain_id=chain_id)
    
    # Handle native tokens
    # 1inch uses the wrapped token address for native tokens
    wrapped_native_token = token_service.get_wrapped_native_token_address(chain_id)
    
    # Replace native token with wrapped token
    if is_native_in:
        token_in = wrapped_native_token
        logger.info(f"Using wrapped token {token_in} for native token")
    
    if is_native_out:
        token_out = wrapped_native_token
        logger.info(f"Using wrapped token {token_out} for native token")
    
    # Convert amount to smallest unit
    amount_in_smallest_unit = int(Decimal(amount) * Decimal(10 ** token_in_decimals))
    
    # Build API URL
    base_url = "https://api.1inch.dev/swap/v5.2"
    
    # Prepare headers with API key
    headers = {
        "Authorization": "Bearer 5NBC0Z3F5GPVMGG1UAPM6HBRBQP6QPVVKJ",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Build query parameters
    params = {
        "src": token_in,
        "dst": token_out,
        "amount": str(amount_in_smallest_unit),
        "slippage": str(slippage),
        "includeTokensInfo": "true",
        "includeProtocols": "true",
        "includeGas": "true"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/{chain_id}/quote"
            logger.info(f"Requesting 1inch quote: {url} with params: {params}")
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"1inch API error: {error_text}")
                    return {"error": f"1inch API error: {error_text}"}
                
                data = await response.json()
                logger.info(f"1inch quote response: {json.dumps(data, indent=2)}")
                
                # Extract relevant data
                src_amount = data.get("fromTokenAmount")
                dest_amount = data.get("toTokenAmount")
                
                # Convert amounts to decimal for display
                src_amount_decimal = Decimal(src_amount) / Decimal(10 ** token_in_decimals)
                dest_amount_decimal = Decimal(dest_amount) / Decimal(10 ** token_out_decimals)
                
                # Calculate price impact
                price_impact = None
                if "estimatedGas" in data:
                    gas_estimate = data["estimatedGas"]
                else:
                    gas_estimate = None
                
                return {
                    "srcAmount": src_amount,
                    "destAmount": dest_amount,
                    "srcAmountDecimal": str(src_amount_decimal),
                    "destAmountDecimal": str(dest_amount_decimal),
                    "priceImpact": price_impact,
                    "gasEstimate": gas_estimate,
                    "rawQuote": data,
                    "aggregator": "1inch"
                }
    except Exception as e:
        logger.error(f"Error getting 1inch quote: {str(e)}")
        return {"error": f"Error getting 1inch quote: {str(e)}"}

async def build_swap_transaction(
    token_in: str,
    token_out: str,
    amount: float,
    chain_id: int,
    slippage: float = 1.0,
    wallet_address: str = None,
    token_in_decimals: Optional[int] = None,
    token_out_decimals: Optional[int] = None,
    is_native_in: Optional[bool] = None,
    is_wrapped_native_in: Optional[bool] = None,
    is_native_out: Optional[bool] = None,
    is_wrapped_native_out: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Build a swap transaction for 1inch.
    
    Args:
        token_in: Input token address
        token_out: Output token address
        amount: Amount to swap
        chain_id: Chain ID
        slippage: Slippage tolerance in percentage
        wallet_address: Wallet address to swap from
        token_in_decimals: Decimals for input token (optional)
        token_out_decimals: Decimals for output token (optional)
        is_native_in: Whether input token is native (optional)
        is_wrapped_native_in: Whether input token is wrapped native (optional)
        is_native_out: Whether output token is native (optional)
        is_wrapped_native_out: Whether output token is wrapped native (optional)
    
    Returns:
        Transaction data
    """
    # Check if chain is supported
    chain_config = get_chain_config(chain_id)
    if not chain_config:
        return {"error": f"Chain {chain_id} not supported"}
    
    if not wallet_address:
        return {"error": "Wallet address is required"}
    
    # Determine if tokens are native or wrapped if not provided
    if is_native_in is None:
        is_native_in = token_service.is_native_token(token_in, chain_id)
    
    if is_wrapped_native_in is None:
        is_wrapped_native_in = token_service.is_wrapped_native_token(token_in, chain_id)
    
    if is_native_out is None:
        is_native_out = token_service.is_native_token(token_out, chain_id)
    
    if is_wrapped_native_out is None:
        is_wrapped_native_out = token_service.is_wrapped_native_token(token_out, chain_id)
    
    # Get token decimals if not provided
    if token_in_decimals is None:
        token_in_decimals = token_service.get_token_decimals(token_address=token_in, chain_id=chain_id)
    
    if token_out_decimals is None:
        token_out_decimals = token_service.get_token_decimals(token_address=token_out, chain_id=chain_id)
    
    # Handle native tokens
    # 1inch uses the wrapped token address for native tokens
    wrapped_native_token = token_service.get_wrapped_native_token_address(chain_id)
    
    # Replace native token with wrapped token
    if is_native_in:
        token_in = wrapped_native_token
        logger.info(f"Using wrapped token {token_in} for native token")
    
    if is_native_out:
        token_out = wrapped_native_token
        logger.info(f"Using wrapped token {token_out} for native token")
    
    # Convert amount to smallest unit
    amount_in_smallest_unit = int(Decimal(amount) * Decimal(10 ** token_in_decimals))
    
    # Build API URL
    base_url = "https://api.1inch.dev/swap/v5.2"
    
    # Prepare headers with API key
    headers = {
        "Authorization": "Bearer 5NBC0Z3F5GPVMGG1UAPM6HBRBQP6QPVVKJ",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Build query parameters
    params = {
        "src": token_in,
        "dst": token_out,
        "amount": str(amount_in_smallest_unit),
        "from": wallet_address,
        "slippage": str(slippage),
        "includeTokensInfo": "true",
        "includeProtocols": "true",
        "includeGas": "true"
    }
    
    # Add disableEstimate=true for native token output
    if is_native_out:
        params["disableEstimate"] = "true"
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{base_url}/{chain_id}/swap"
            logger.info(f"Requesting 1inch swap: {url} with params: {params}")
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"1inch API error: {error_text}")
                    return {"error": f"1inch API error: {error_text}"}
                
                data = await response.json()
                logger.info(f"1inch swap response: {json.dumps(data, indent=2)}")
                
                # Extract transaction data
                tx = data.get("tx", {})
                
                # Adjust value if input token is native
                if is_native_in:
                    tx["value"] = str(amount_in_smallest_unit)
                
                return {
                    "tx": tx,
                    "rawResponse": data,
                    "aggregator": "1inch"
                }
    except Exception as e:
        logger.error(f"Error building 1inch swap: {str(e)}")
        return {"error": f"Error building 1inch swap: {str(e)}"} 