from abc import ABC, abstractmethod
from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SourceT(ABC, BaseModel, Generic[T]):
    @abstractmethod
    async def get_data(self) -> Sequence[T]:
        """Load data to be parsed for commands/questions"""

    async def handle(self, data: T) -> None:
        """Handle the data"""

    async def has_handled(
        self,
        data: T,
    ) -> bool:
        """Check if the bot has already handled the data"""
        return False

    async def mark_as_handled(
        self,
        data: T,
    ) -> None:
        """Mark a data as handled so you don't handle it twice"""
