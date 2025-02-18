from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
U = TypeVar("U")


class Processor(ABC, BaseModel, Generic[T, U]):
    @abstractmethod
    async def process(self, command: T) -> U: ...
