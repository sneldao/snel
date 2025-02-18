import asyncio
import logging
import os
from typing import Literal

from emp_agents.providers import AnthropicModelType, AnthropicProvider
from eth_rpc import set_alchemy_key

from dowse import NoOpExecutor, Pipeline, Processor, logger
from dowse.impls.basic.effects.printer import Printer
from dowse.impls.basic.llms import BasicTweetClassifier
from dowse.impls.basic.llms.commands import BasicTwitterCommands
from dowse.impls.basic.llms.questions import BasicTwitterQuestion
from dowse.impls.basic.source import TwitterMock
from dowse.models import AgentMessage, Tweet

logger.setLevel(logging.DEBUG)
set_alchemy_key(os.environ["ALCHEMY_KEY"])


class TweetWithUserHistory(Tweet):
    user_history: list[str]


class LoadUserData(Processor[Tweet, TweetWithUserHistory]):
    async def format(self, command: Tweet) -> AgentMessage[TweetWithUserHistory]:
        return AgentMessage(
            content=TweetWithUserHistory(
                **command.model_dump(),
                user_history=[
                    "this is a really nice person",
                    "they love AI",
                ],
            ),
            error_message=None,
        )


async def amain():
    pipeline = Pipeline[
        Tweet, TweetWithUserHistory, Literal["commands", "question", "neither"]
    ](
        # preprocessors converts the data to the desired format
        processors=[
            LoadUserData(),
        ],
        # classifier is used to classify the tweet to determine which handler will be used
        classifier=BasicTweetClassifier,
        # each handler can have its own preprocessing, effects, etc.
        handlers={
            # effects can be added after the command using the >> operator
            "commands": BasicTwitterCommands >> Printer(),
            "question": BasicTwitterQuestion >> Printer(),
            "neither": NoOpExecutor >> Printer(),
        },
        source=TwitterMock(),
    )
    await pipeline.run(max_executions=3, iteration_min_time=120)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
