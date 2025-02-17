from abc import abstractmethod
from typing import AsyncIterator

from dowse.models import Tweet

from .source import SourceT


class TwitterSourceT(SourceT[Tweet]):
    @abstractmethod
    def get_data(self) -> AsyncIterator[Tweet]:
        """Load tweets to be parsed for commands/questions"""

    @abstractmethod
    async def handle(self, tweet: Tweet) -> None:
        """Handle a tweet"""
