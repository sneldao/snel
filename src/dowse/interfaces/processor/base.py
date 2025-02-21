from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from dowse.models import AgentMessage

T = TypeVar("T")
U = TypeVar("U")


class Processor(ABC, BaseModel, Generic[T, U]):
    @abstractmethod
    async def process(self, command: T) -> AgentMessage[U]: ...
