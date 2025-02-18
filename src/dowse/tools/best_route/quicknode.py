import os

import httpx
from eth_typing import HexAddress, HexStr
from pydantic import BaseModel, Field

from dowse.logger import logger

QUICKNODE_ENDPOINT = os.environ["QUICKNODE_ENDPOINT"]


class Quote(BaseModel):
    token_in: HexAddress = Field(alias="tokenIn")
    token_out: HexAddress = Field(alias="tokenOut")
    amount_in: int = Field(alias="amountIn")
    amount_out: int = Field(alias="amountOut")
    gas: int
    amount_out_min: float = Field(alias="amountOutMin")
    aggregator: str


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
    token_out: HexAddress,
    amount: int,
    slippage: float,
    chain_id: int,
    recipient: HexAddress,
    token_in: HexAddress,
):
    url = f"{QUICKNODE_ENDPOINT}/addon/688/quote"

    if token_in.lower() == "eth":
        token_in = HexAddress(HexStr("0x4200000000000000000000000000000000000006"))

    tries = 0
    while tries < 3:
        tries += 1
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
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
                    timeout=20,
                )
                data = response.json()
                if data.get("message") == "Internal Server Error":
                    raise Exception("Internal Server Error")
                return data
        except Exception as e:
            logger.error("ERROR GETTING QUOTE", e)

    raise ValueError("Failed to get quote.  Most likely an API Limit")


async def swap(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    slippage: float,
    chain_id: int,
    recipient: HexAddress,
    aggregator: str,
):
    url = f"{QUICKNODE_ENDPOINT}/addon/688/swap"
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
