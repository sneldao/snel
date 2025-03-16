"""
Kyber aggregator service.
"""
import logging
from typing import Dict, Any, Optional, Union
import httpx

logger = logging.getLogger(__name__)

# Define router addresses by chain for Kyber
KYBER_ROUTER_ADDRESSES = {
    1: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Ethereum
    137: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Polygon
    42161: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Arbitrum
    10: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Optimism
    8453: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Base
    534352: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Scroll
}

async def get_kyber_quote(
    http_client: httpx.AsyncClient,
    token_in: Union[str, Dict],
    token_out: Union[str, Dict],
    amount_in_smallest_units: int,
    chain_id: int,
    recipient: str,
    slippage_percentage: float = 1.0
) -> Optional[Dict[str, Any]]:
    """
    Get quote from Kyber API v1.
    
    Args:
        http_client: HTTP client to use for requests
        token_in: Input token address or token info dict
        token_out: Output token address or token info dict
        amount_in_smallest_units: Amount to swap in smallest units
        chain_id: Chain ID
        recipient: Recipient address
        slippage_percentage: Slippage percentage
        
    Returns:
        Quote data or None if not available
    """
    try:
        # Extract addresses
        token_in_address = token_in["address"] if isinstance(token_in, dict) else token_in
        token_out_address = token_out["address"] if isinstance(token_out, dict) else token_out

        # Step 1: Get the route data
        base_url = "https://aggregator-api.kyberswap.com"
        route_endpoint = f"/{_get_chain_name(chain_id)}/api/v1/routes"

        route_params = {
            "tokenIn": token_in_address,
            "tokenOut": token_out_address,
            "amountIn": str(amount_in_smallest_units)
        }

        logger.info(f"Getting Kyber route for {token_in_address} to {token_out_address} with amount {amount_in_smallest_units}")
        route_response = await http_client.get(
            f"{base_url}{route_endpoint}",
            params=route_params
        )
        route_response.raise_for_status()
        route_data = route_response.json()
        
        # Log the route response for debugging
        logger.debug(f"Kyber route response: {route_data}")
        
        # Check for required fields
        if 'data' not in route_data:
            raise ValueError(f"Missing 'data' in Kyber response: {route_data}")
        
        if 'routeSummary' not in route_data['data']:
            raise ValueError(f"Missing 'routeSummary' in Kyber response data: {route_data['data']}")
            
        router_address = route_data['data'].get('routerAddress') or get_router_address(chain_id)
            
        # Step 2: Get the encoded swap data using the routeSummary
        # FIXED: Use the correct endpoint from the documentation
        encode_endpoint = f"/{_get_chain_name(chain_id)}/api/v1/route/build"
        
        # Format the request body according to KyberSwap documentation
        encode_body = {
            "routeSummary": route_data['data']['routeSummary'],
            "sender": recipient,
            "recipient": recipient,
            "slippageTolerance": int(slippage_percentage * 100)  # Convert percentage to basis points
        }
        
        logger.info(f"Getting Kyber encoded swap data with slippage {slippage_percentage}%")
        encode_response = await http_client.post(
            f"{base_url}{encode_endpoint}",
            json=encode_body
        )
        encode_response.raise_for_status()
        encode_data = encode_response.json()
        
        # Log the encode response for debugging
        logger.debug(f"Kyber encode response: {encode_data}")
        
        # Check for required fields
        if 'data' not in encode_data:
            raise ValueError(f"Missing 'data' in Kyber encode response: {encode_data}")
            
        # Per the documentation, the encoded data is directly in the data field
        if not encode_data['data'].get('data'):
            raise ValueError(f"Missing 'data.data' in Kyber encode response: {encode_data['data']}")
        
        # Format Kyber response to match expected format
        buy_amount = str(route_data['data']['routeSummary']["amountOut"])
        min_amount_out = str(int(float(buy_amount) * (1 - slippage_percentage / 100)))
        
        # Check if this is a native token swap (ETH)
        is_native_token = token_in_address.lower() == "0x0000000000000000000000000000000000000000"
        
        return {
            "to": router_address,
            "data": encode_data['data']['data'],  # Use the actual encoded transaction data
            "value": str(amount_in_smallest_units if is_native_token else 0),
            "gas": str(route_data['data']['routeSummary'].get("gas", "500000")),
            "buy_amount": buy_amount,
            "sell_amount": str(amount_in_smallest_units),
            "price": route_data['data']['routeSummary'].get("amountOutUsd"),
            "protocol": "kyberswap",
            "gas_usd": str(route_data['data']['routeSummary'].get("gasUsd", "0")),
            "minimum_received": min_amount_out,
            "aggregator": "kyber"
        }
    except Exception as e:
        logger.error(f"Kyber API error: {str(e)}")
        # Re-raise the exception to be caught by the caller
        raise

def get_router_address(chain_id: int) -> str:
    """Get the router address for a specific chain."""
    return KYBER_ROUTER_ADDRESSES.get(chain_id, KYBER_ROUTER_ADDRESSES[1])  # Default to Ethereum

def _get_chain_name(chain_id: int) -> str:
    """Get chain name for API endpoints"""
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
        raise ValueError(f"Chain {chain_id} not supported by Kyber")

    return chain
