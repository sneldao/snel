from typing import Awaitable

from pydantic import Field

from dowse.interfaces.effects import Effect
from dowse.interfaces.sources.twitter import Tweet

from ..llms.commands import CommandsList
from ..llms.questions import Response


class Printer(Effect[Tweet, CommandsList | Response]):
    prefix: str = Field(default="PRINTER")

    def execute(
        self, input_: Tweet, output: CommandsList | Response
    ) -> Awaitable[None]:
        print(f"{self.prefix}:", output)
        return None
