import ast
import json
from typing import Callable

from pydantic import BaseModel

from dowse.interfaces.processor.base import Processor
from dowse.models import Tweet
from dowse.tools import convert_dollar_amount_to_eth, get_token_address_tool


class FormattedCommand(BaseModel):
    user_request: str
    caller: str

    @property
    def tokens(self) -> dict[str, str]:
        return ast.literal_eval(self.token_mapping)


class ProcessTokens(Processor[Tweet, FormattedCommand]):
    tools: list[Callable] = [
        get_token_address_tool,
        convert_dollar_amount_to_eth,
    ]

    async def to_string(self, command: Tweet) -> str:
        return json.dumps({"caller": command.creator_name, "content": command.content})


token_processor = ProcessTokens()
