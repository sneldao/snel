"""
0x Protocol aggregator service.
"""
import contextlib
import logging
import os
from typing import Dict, Any, Optional, Union
import httpx

logger = logging.getLogger(__name__)

async def get_zerox_quote(
    http_client: httpx.AsyncClient,
    token_in: Union[str, Dict],
    token_out: Union[str, Dict],
    amount: int,
    chain_id: int,
    wallet_address: str,
    slippage_percentage: float = 1.0
) -> Optional[Dict[str, Any]]:
    """
    Get quote from 0x API using the Permit2 endpoint with improved handling.
    
    Args:
        http_client: HTTP client to use for requests
        token_in: Input token address or token info dict
        token_out: Output token address or token info dict
        amount: Amount to swap in smallest units
        chain_id: Chain ID
        wallet_address: Wallet address
        slippage_percentage: Slippage percentage
        
    Returns:
        Quote data or None if not available
    """
    try:
        # Extract addresses
        token_in_address = token_in["address"] if isinstance(token_in, dict) else token_in
        token_out_address = token_out["address"] if isinstance(token_out, dict) else token_out

        # Check if chain is supported by 0x
        supported_chains = [1, 10, 56, 137, 8453, 42161, 43114, 59144, 534352, 5000, 34443, 81457, 10143]
        if chain_id not in supported_chains:
            logger.warning(f"Chain {chain_id} not supported by 0x API")
            raise ValueError(f"Chain {chain_id} not supported by 0x API")

        # Use environment variable for API key
        api_key = os.getenv("ZEROX_API_KEY", "")
        if not api_key:
            logger.warning("No 0x API key found in environment variables. This may lead to rate limiting or failures.")

        # Determine base URL based on chain
        base_url = "https://api.0x.org"

        # Use the permit2 quote endpoint for v2 API
        endpoint = "/swap/permit2/quote"

        params = {
            "sellToken": token_in_address,
            "buyToken": token_out_address,
            "sellAmount": str(amount),
            "taker": wallet_address,
            "chainId": chain_id,
            "skipValidation": "false",
            "enableSlippageProtection": "true"
        }

        headers = {
            "0x-api-key": api_key,
            "0x-version": "v2"  # Use v2 of the API
        }

        logger.info(f"Getting 0x quote for {token_in_address} to {token_out_address} with amount {amount}")
        response = await http_client.get(
            f"{base_url}{endpoint}",
            params=params,
            headers=headers
        )

        response.raise_for_status()
        data = response.json()

        # Log the full response for debugging
        logger.debug(f"0x response: {data}")

        # Check if we have the required fields
        if 'buyAmount' not in data or 'transaction' not in data:
            logger.error(f"Missing required fields in 0x response: {data}")
            raise ValueError("Invalid 0x response format")

        # Get a reasonable gas estimate
        gas_estimate = data['transaction'].get('gas', '300000')
        if gas_estimate:
            # Parse to int and apply a reasonable cap if it's too high
            try:
                gas_int = int(gas_estimate)
                # Cap at 500,000 if it's over 1,000,000
                if gas_int > 1000000:
                    logger.warning(f"0x provided very high gas estimate: {gas_int}, capping at 500000")
                    gas_estimate = "500000"
            except (ValueError, TypeError):
                logger.warning(f"Could not parse 0x gas estimate: {gas_estimate}, using default")
                gas_estimate = "300000"  # Fallback to a reasonable value

        # Ensure value field is properly formatted 
        value = data['transaction'].get('value', '0')
        if value == '' or value is None:
            value = '0'

        # Extract min_buy_amount (minBuyAmount or guaranteedPrice * sellAmount)
        min_buy_amount = data.get('minBuyAmount')

        # If minBuyAmount is not available, use guaranteedPrice calculation
        if not min_buy_amount and 'guaranteedPrice' in data and data['guaranteedPrice']:
            try:
                guaranteed_price = float(data['guaranteedPrice'])
                sell_amount = float(amount)
                min_buy_amount = str(int(guaranteed_price * sell_amount * 0.99))  # 99% of expected amount as minimum
                logger.info(f"Calculated min_buy_amount from guaranteedPrice: {min_buy_amount}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error calculating min_buy_amount from guaranteedPrice: {e}")
                min_buy_amount = data.get('buyAmount', '0')  # Fallback to buyAmount

        # If both methods fail, fall back to buyAmount
        if not min_buy_amount:
            min_buy_amount = data.get('buyAmount', '0')

        # Get protocol/source information
        protocol = "0x"
        if 'route' in data:
            if 'fills' in data['route'] and len(data['route']['fills']) > 0:
                protocol = data['route']['fills'][0].get('source', '0x')
            elif 'sources' in data['route'] and len(data['route']['sources']) > 0:
                # Find the source with the highest proportion
                max_proportion = 0
                for source in data['route']['sources']:
                    if source.get('proportion', 0) > max_proportion:
                        protocol = source.get('name', '0x')
                        max_proportion = source.get('proportion', 0)

        # Format response for frontend consumption
        return {
            "to": data['transaction']['to'],
            "data": data['transaction']['data'],
            "value": value,
            "gas": gas_estimate,
            "buy_amount": data['buyAmount'],
            "sell_amount": str(amount),
            "protocol": protocol,
            "gas_usd": data.get('estimatedGas', data.get('totalNetworkFee', '0')),
            "price": data.get('guaranteedPrice', data.get('price')),
            "minimum_received": min_buy_amount,
            "guaranteedPrice": data.get('guaranteedPrice'),  # Include the guaranteed price directly
            "aggregator": "0x"
        }
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                error_msg = f"{error_msg}: {e.response.text}"
            if hasattr(e.response, 'status_code'):
                error_msg = f"Status {e.response.status_code} - {error_msg}"

            # If there was a JSON response with more details, try to extract it
            if hasattr(e.response, 'json'):
                with contextlib.suppress(Exception):
                    error_json = e.response.json()
                    logger.error(f"0x API error details: {error_json}")
                    if 'validationErrors' in error_json:
                        for err in error_json['validationErrors']:
                            logger.error(f"Validation error: {err.get('reason', 'Unknown')}")
        logger.error(f"0x API error: {error_msg}")
        raise
