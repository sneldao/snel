import os
from typing import Literal

import httpx
from eth_typing import HexAddress, HexStr
from pydantic import BaseModel, Field

from dowse.logger import logger


def get_quicknode_endpoint() -> str:
    endpoint = os.environ.get("QUICKNODE_ENDPOINT")
    if not endpoint:
        raise ValueError("QUICKNODE_ENDPOINT environment variable is required")
    return endpoint


class Quote(BaseModel):
    token_in: HexAddress = Field(alias="tokenIn")
    token_out: HexAddress = Field(alias="tokenOut")
    amount_in: int = Field(alias="amountIn")
    amount_out: int = Field(alias="amountOut")
    gas: int
    amount_out_min: float = Field(alias="amountOutMin")
    aggregator: str = "quicknode"


class Quotes(BaseModel):
    quotes: list[Quote]


class SwapResponse(BaseModel):
    from_: HexAddress = Field(alias="from")
    to: HexAddress
    data: str
    value: int
    chain_id: int = Field(alias="chainId")
    aggregator: str


async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    chain_id: Literal[1, 8453, 42161, 10, 137, 43114] = 8453,
) -> Quote:
    # Get endpoint when needed
    quicknode_endpoint = get_quicknode_endpoint()
    
    chain = get_chain_from_chain_id(chain_id)
    base_url = "https://api.quicknode.com"
    path = f"{chain}/api/v1/routes"
    params = {"tokenIn": token_in, "tokenOut": token_out, "amountIn": amount}
    url = f"{base_url}/{path}?tokenIn={params['tokenIn']}&tokenOut={params['tokenOut']}&amountIn={params['amountIn']}"

    tries = 0
    while tries < 3:
        tries += 1
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response_json = response.json()
                data = response_json.get("data")
                route_summary = data.get("routeSummary")
                return Quote(
                    token_in=route_summary.get("tokenIn"),
                    token_out=route_summary.get("tokenOut"),
                    amount_in=route_summary.get("amountIn"),
                    amount_out=route_summary.get("amountOut"),
                    gas=route_summary.get("gas"),
                )
        except Exception as e:
            logger.error("ERROR GETTING QUOTE: %s", e)

    raise ValueError("Failed to get quote. Most likely an API Limit")


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


async def swap(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    slippage: float,
    chain_id: int,
    recipient: HexAddress,
    aggregator: str,
) -> SwapResponse:
    # Get endpoint when needed
    quicknode_endpoint = get_quicknode_endpoint()
    url = f"{quicknode_endpoint}/addon/688/swap"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={
                "aggregator": aggregator,
                "tokenIn": token_in,
                "tokenOut": token_out,
                "amountIn": amount,
                "slippage": slippage,
                "chainId": chain_id,
                "recipient": recipient,
            },
            headers={
                "Content-Type": "application/json",
            },
        )
        return SwapResponse(**response.json())
