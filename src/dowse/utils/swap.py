import os

import httpx
from eth_rpc import PrivateKeyWallet
from eth_typing import HexAddress, HexStr
from pydantic import BaseModel, Field

QUICKNODE_ENDPOINT = os.getenv("QUICKNODE_ENDPOINT")


class SwapResponse(BaseModel):
    from_: HexAddress = Field(alias="from")
    to: HexAddress
    data: str
    value: int
    chain_id: int = Field(alias="chainId")
    aggregator: str


async def execute_swap(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    slippage: float,
    chain_id: int,
    recipient: HexAddress,
    aggregator: str,
    wallet: PrivateKeyWallet,
) -> HexStr:
    """Sends a raw swap from the quicknode endpoint and returns the tx hash"""

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
    swap_data = SwapResponse(**response.json())

    signed_tx = wallet.prepare_and_sign(
        data=HexStr(swap_data.data),
        to=swap_data.to,
        value=swap_data.value,
    )

    tx_hash = await wallet.send_raw_transaction(signed_tx.raw_transaction)
    return tx_hash
