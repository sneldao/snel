import os

import httpx


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
            print("ERROR GETTING TOKEN FOR SYMBOL", e)

    raise ValueError("Failed to get token for symbol.  Most likely an API Limit")
