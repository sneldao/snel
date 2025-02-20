from datetime import datetime
from typing import Annotated

import httpx
from pydantic import BaseModel
from typing_extensions import Doc


class Weather(BaseModel):
    temperature: str
    wind: str
    description: str
    forecast: list[dict[str, str]]


async def get_current_weather(
    location: Annotated[str, Doc("The location to get the weather for")]
) -> str:
    """Gets the weather for a given location"""

    url = f"https://goweather.herokuapp.com/weather/{location.replace(' ', '').lower()}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        weather_data = response.json()
    return Weather(**weather_data).model_dump_json()


def current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


TOOLS = [
    get_current_weather,
    current_time,
]
