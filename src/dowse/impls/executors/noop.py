from typing import Any

from dowse.interfaces import Executor
from dowse.models import AgentMessage


class NoOpExecutor(Executor[Any, None]):
    async def execute(
        self,
        input_: Any,
        persist: bool = False,
    ) -> AgentMessage[None]:
        return AgentMessage(content=None, error_message=None)
