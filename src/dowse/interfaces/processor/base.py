from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from dowse.models import AgentMessage

T = TypeVar("T")
U = TypeVar("U")


class Processor(ABC, BaseModel, Generic[T, U]):
    async def process(self, command: T) -> AgentMessage[U]:
        try:
            return AgentMessage(
                content=await self.execute(command),
                error_message=None,
            )
        except Exception as e:
            return AgentMessage(
                content=None,
                error_message=str(e),
            )

    @abstractmethod
    async def execute(self, command: T) -> U: ...
