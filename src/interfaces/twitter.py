from abc import ABC, abstractmethod

from pydantic import BaseModel


class Tweet(BaseModel):
    id: int
    content: str
    creator_id: int
    creator_name: str


class TwitterT(ABC):
    @abstractmethod
    async def get_tweets(self) -> list[Tweet]:
        """Load tweets to be parsed for commands/questions"""

    @abstractmethod
    async def respond(self, tweet_id: int, content: str) -> None:
        """Respond to a tweet"""

    @abstractmethod
    async def has_responded(
        self,
        tweet_id: int,
    ) -> bool:
        """Check if the bot has already responded to a tweet"""

    @abstractmethod
    async def mark_as_responded(
        self,
        tweet_id: int,
    ) -> None:
        """Mark a tweet as responded to so you don't respond to it twice"""
