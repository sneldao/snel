import os

import httpx

from dowse.exceptions import TokenNotFoundError

from ..logger import logger


async def get_token_address(symbol: str, chain: str = "base") -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.dexscreener.com/latest/dex/search?q={symbol}&chain={chain}",
            timeout=20,
        )
    pairs = response.json()["pairs"]
    addresses = set()
    for pair in pairs:
        if pair["chainId"] != chain:
            continue
        quote = pair["quoteToken"]
        base = pair["baseToken"]

        if quote["symbol"] == symbol:
            addresses.add(quote["address"])
        elif base["symbol"] == symbol:
            addresses.add(base["address"])

    if len(addresses) == 0:
        raise TokenNotFoundError(f"Failed to find token for symbol: {symbol}")
    if len(addresses) > 1:
        raise TokenNotFoundError(
            f"Failed to find token for symbol: {symbol}, multiple existing tokens found: {addresses}"
        )
    return list(addresses)[0]


async def get_token_for_symbol(symbol: str) -> str:
    headers = {
        "accept": "application/json",
        "X-API-Key": os.environ["MORALIS_API_KEY"],
    }

    params = {
        "chain": "base",
        "symbols": [symbol],
    }

    tries = 0
    while tries < 3:
        tries += 1
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://deep-index.moralis.io/api/v2.2/erc20/metadata/symbols",
                    params=params,
                    headers=headers,
                    timeout=20,
                )
                data = response.json()
                return data[0]["address"]
        except Exception as e:
            logger.error("ERROR GETTING TOKEN FOR SYMBOL", e)

    raise ValueError("Failed to get token for symbol.  Most likely an API Limit")
