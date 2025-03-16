"""
OpenOcean aggregator service.
"""
import logging
from typing import Dict, Any, Optional, Union
import httpx

logger = logging.getLogger(__name__)

async def get_openocean_quote(
    http_client: httpx.AsyncClient,
    token_in: Union[str, Dict],
    token_out: Union[str, Dict],
    amount: float,
    chain_id: int,
    wallet_address: str,
    slippage_percentage: float = 1.0,
    chain_name_func = None
) -> Optional[Dict[str, Any]]:
    """
    Get quote from OpenOcean API.
    
    Args:
        http_client: HTTP client to use for requests
        token_in: Input token address or token info dict
        token_out: Output token address or token info dict
        amount: Amount to swap in smallest units
        chain_id: Chain ID
        wallet_address: Wallet address
        slippage_percentage: Slippage percentage
        chain_name_func: Function to get chain name from chain ID
        
    Returns:
        Quote data or None if not available
    """
    try:
        # Extract addresses
        token_in_address = token_in["address"] if isinstance(token_in, dict) else token_in
        token_out_address = token_out["address"] if isinstance(token_out, dict) else token_out

        # Get chain name
        if chain_name_func:
            chain_name = chain_name_func(chain_id)
        else:
            chain_name = _get_chain_name(chain_id)

        base_url = "https://open-api.openocean.finance"
        endpoint = f"/v4/{chain_name}/quote"

        params = {
            "inTokenAddress": token_in_address,
            "outTokenAddress": token_out_address,
            "amount": str(amount),
            "gasPrice": "5",
            "slippage": str(slippage_percentage),
            "account": wallet_address
        }

        response = await http_client.get(
            f"{base_url}{endpoint}",
            params=params
        )
        response.raise_for_status()
        quote_data = response.json()
        
        if quote_data["code"] != 200 or "data" not in quote_data:
            raise ValueError(f"Invalid OpenOcean quote response: {quote_data}")
        
        # Then get the swap data
        swap_url = f"{base_url}/v4/{chain_name}/swap"
        swap_response = await http_client.get(swap_url, params=params)
        swap_response.raise_for_status()
        swap_data = swap_response.json()
        
        if swap_data["code"] != 200 or "data" not in swap_data:
            raise ValueError(f"Invalid OpenOcean swap response: {swap_data}")
        
        # Combine data from both endpoints
        return {
            "to": swap_data["data"]["to"],
            "data": swap_data["data"]["data"],
            "value": swap_data["data"].get("value", "0"),
            "gas": str(swap_data["data"].get("estimatedGas", "500000")),
            "buy_amount": str(quote_data["data"]["outAmount"]),
            "sell_amount": str(amount),
            "price": quote_data["data"].get("price"),
            "protocol": "openocean",
            "gas_usd": str(swap_data["data"].get("estimatedGasUsd", "0")),
            "aggregator": "openocean"
        }
    except Exception as e:
        logger.error(f"OpenOcean API error: {str(e)}")
        raise

def _get_chain_name(chain_id: int) -> str:
    """Get chain name for API endpoints"""
    chain_mapping = {
        1: "eth",  # OpenOcean uses "eth", Kyber uses "ethereum"
        10: "optimism",
        137: "polygon",
        42161: "arbitrum",
        8453: "base",
        534352: "scroll"
    }

    chain = chain_mapping.get(chain_id)
    if not chain:
        raise ValueError(f"Chain {chain_id} not supported by OpenOcean")

    return chain
