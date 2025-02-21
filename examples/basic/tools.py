import json
from datetime import datetime
from typing import Annotated

import httpx
from typing_extensions import Doc


async def lookup_zip_code(
    zip_code: Annotated[str, Doc("The zip code to lookup")]
) -> str:
    """Looks up the city and state for a given zip code"""

    url = f"https://api.zippopotam.us/us/{zip_code}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        zip_code_data = response.json()
    return json.dumps(zip_code_data)


def current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = [
    lookup_zip_code,
    current_time,
]
