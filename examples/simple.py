import asyncio
import logging
from typing import Literal

from pydantic import BaseModel

from dowse import Pipeline, logger
from dowse.impls.basic.effects import Printer
from dowse.interfaces.executor import Executor
from dowse.interfaces.llms.classifier import Classifier
from dowse.interfaces.sources import SourceT

logger.setLevel(logging.DEBUG)


class Food(BaseModel):
    name: str


FoodClassifier = Classifier[Food, Literal["breakfast", "lunch", "dinner"]](
    prompt="""
        classify the food as whichever meal it most reminds you of.
        there are no wrong answers but try to guess what the average person would choose.
    """,
)


class FoodSource(SourceT[Food]):
    async def get_data(self) -> list[Food]:
        return [
            Food(name="hashbrowns"),
            Food(name="meatloaf"),
            Food(name="BLT"),
        ]


BreakfastExecutor = Executor[Food, str, str](
    prompt="Write a joke about the breakfast food the user tells you",
)

LunchExecutor = Executor[Food, str, str](
    prompt="Say something really serious, but mention the lunch food the user tells you.  Less than 100 words.",
)

DinnerExecutor = Executor[Food, str, str](
    prompt="Say something really sad, but mention the dinner food the user tells you.  Less than 100 words.",
)


async def amain():
    pipeline = Pipeline[Literal["breakfast", "lunch", "dinner"]](
        classifier=FoodClassifier,
        handlers={
            # You can provide effects to be executed after the command is parsed using the >> operator
            "breakfast": BreakfastExecutor >> Printer(prefix="BREAKFAST"),
            "lunch": LunchExecutor >> Printer(prefix="LUNCH"),
            "dinner": DinnerExecutor >> Printer(prefix="DINNER"),
        },
        source=FoodSource(),
    )
    await pipeline.run(max_executions=3, iteration_min_time=120)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
