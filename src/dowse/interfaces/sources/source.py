from abc import ABC, abstractmethod
from typing import AsyncIterator, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SourceT(ABC, BaseModel, Generic[T]):
    @abstractmethod
    def get_data(self) -> AsyncIterator[T]:
        """Load data to be parsed for commands/questions"""

    @abstractmethod
    async def handle(self, data: T) -> None:
        """Handle the data"""

    @abstractmethod
    async def has_handled(
        self,
        data: T,
    ) -> bool:
        """Check if the bot has already handled the data"""

    @abstractmethod
    async def mark_as_handled(
        self,
        data: T,
    ) -> None:
        """Mark a data as handled so you don't handle it twice"""
