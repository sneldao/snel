import os
from typing import Literal

import httpx
from eth_typing import HexAddress, HexStr
from pydantic import BaseModel

from dowse.logger import logger

QUICKNODE_ENDPOINT = os.environ["QUICKNODE_ENDPOINT"]


class Quote(BaseModel):
    token_in: HexAddress
    token_out: HexAddress
    amount_in: int
    amount_out: int
    gas: int
    aggregator: str = "kyber"


async def get_quote(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    chain_id: Literal[1, 8453, 42161, 10, 137, 43114] = 8453,
) -> Quote:
    chain = get_chain_from_chain_id(chain_id)
    if token_in.lower() == "eth":
        token_in = HexAddress(HexStr("0x4200000000000000000000000000000000000006"))

    base_url = "https://aggregator-api.kyberswap.com"
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

    raise ValueError("Failed to get quote.  Most likely an API Limit")


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
