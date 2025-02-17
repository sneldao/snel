import json
from typing import Callable

from pydantic import BaseModel

from dowse.interfaces.processor.base import Processor
from dowse.models import Tweet
from dowse.tools import convert_dollar_amount_to_eth, get_token_address_tool


class FormattedCommand(BaseModel):
    content: str
    caller: str


class ProcessTokens(Processor[Tweet, FormattedCommand]):
    tools: list[Callable] = [
        get_token_address_tool,
        convert_dollar_amount_to_eth,
    ]

    async def to_string(self, command: Tweet) -> str:
        return json.dumps({"caller": command.creator_name, "content": command.content})
