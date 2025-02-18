import asyncio
import logging
from typing import Callable, Literal

from dowse import Pipeline, logger
from dowse.impls.basic.effects import Printer
from dowse.impls.executors import NoOpExecutor
from dowse.interfaces import Classifier, Executor, Processor, SourceT, Tweet

logger.setLevel(logging.DEBUG)


BetClassifier = Classifier[Tweet, Literal["is_bet", "bet_information", "neither"]](
    prompt="""
        classify whether the tweet is a bet, asking for information about a bet, or neither.
    """,
)


class BetSource(SourceT[Tweet]):
    async def get_data(self) -> list[Tweet]:
        return [
            Tweet(
                id=1,
                creator_id=1,
                creator_name="John Doe",
                content="I bet $100 on the Lakers to win the NBA Finals",
            ),
            Tweet(
                id=2,
                creator_id=2,
                creator_name="Jane Doe",
                content="I want to know the odds for the Lakers to win the NBA Finals",
            ),
            Tweet(
                id=3,
                creator_id=3,
                creator_name="John Smith",
                content="I'm not sure if I want to bet on the Lakers to win the NBA Finals",
            ),
        ]


async def get_bet_odds_tool(tweet: Tweet) -> str:
    return "odds are 100 to 1"


class BetOddsLookup(Processor[Tweet, Tweet]):
    tools: list[Callable] = [
        get_bet_odds_tool,
    ]


# we specify the input type, the processed type, and the output type
BetExecutor = Executor[Tweet, Tweet, str](
    prompt="Execute a user's finalized bet",
)
BetInformationExecutor = Executor[Tweet, Tweet, str](
    prompt="Lookup the information for a bet",
    preprocessors=[BetOddsLookup()],
)


async def amain():
    pipeline = Pipeline[Tweet, Literal["is_bet", "bet_information", "neither"]](
        classifier=BetClassifier,
        preprocessors=[
            BetOddsLookup(),
        ],
        handlers={
            "is_bet": BetExecutor >> Printer(prefix="BET"),
            "bet_information": (
                BetInformationExecutor >> Printer(prefix="BET INFORMATION")
            ),
            "neither": NoOpExecutor,
        },
        source=BetSource(),
    )
    await pipeline.run(max_executions=3, iteration_min_time=120)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
