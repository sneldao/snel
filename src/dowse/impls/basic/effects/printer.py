from pydantic import Field

from dowse.interfaces.effects import Effect
from dowse.models import Tweet

from ..llms.commands import CommandsList
from ..llms.questions import Response


class Printer(Effect[Tweet, CommandsList | Response]):
    prefix: str = Field(default="PRINTER")

    async def execute(
        self,
        input_: Tweet,
        output: CommandsList | Response,
    ) -> None:
        print(f"{self.prefix}:", output)
        return None
