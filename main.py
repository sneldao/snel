import asyncio
import logging
import os
from typing import Literal

from eth_rpc import set_alchemy_key

from dowse import Pipeline, logger
from dowse.impls.basic import (
    BasicTweetClassifier,
    BasicTwitterCommands,
    BasicTwitterQuestion,
    Printer,
    TwitterMock,
)
from dowse.models import Tweet

logger.setLevel(logging.DEBUG)
set_alchemy_key(os.environ["ALCHEMY_KEY"])


async def amain():
    pipeline = Pipeline[Tweet, Tweet, Literal["commands", "question"]](
        classifier=BasicTweetClassifier,
        handlers={
            # You can provide effects to be executed after the command is parsed using the >> operator
            "commands": BasicTwitterCommands.add_effect(Printer()),
            "question": BasicTwitterQuestion.add_effects([Printer()]),
        },
        source=TwitterMock(),
    )
    await pipeline.run(max_executions=3, iteration_min_time=120)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
