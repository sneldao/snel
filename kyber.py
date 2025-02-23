from typing import Optional
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx

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
            "clientData": {
                "source": "pointless"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 404:
                raise NoRouteFoundError("No valid route found for this swap")
            elif response.status_code == 400:
                data = response.json()
                if "insufficient liquidity" in str(data).lower():
                    raise InsufficientLiquidityError("Not enough liquidity for this swap")
                elif "invalid token" in str(data).lower():
                    raise InvalidTokenError(f"Invalid token address: {data.get('message')}")
                else:
                    raise BuildTransactionError(f"Failed to build swap: {data.get('message')}")
            
            response.raise_for_status()
            data = response.json()
            
            if "tx" not in data:
                raise BuildTransactionError("Missing transaction data in response")
            
            return KyberQuote(
                router_address=data["tx"]["to"],
                data=data["tx"]["data"],
                gas=data["tx"]["gas"]
            )
            
    except httpx.HTTPError as e:
        raise KyberSwapError(f"HTTP error occurred: {str(e)}")
    except Exception as e:
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