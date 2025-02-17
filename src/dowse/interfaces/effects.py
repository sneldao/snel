from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction
from typing import Awaitable, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
U = TypeVar("U")


class Effect(ABC, BaseModel, Generic[T, U]):
    @abstractmethod
    def execute(self, input_: T, output: U) -> Awaitable[None] | None: ...

    async def __call__(self, input: T, output: U) -> Awaitable[None] | None:
        if iscoroutinefunction(self.execute):
            return await self.execute(input, output)
        return self.execute(input, output)
