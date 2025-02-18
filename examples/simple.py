import asyncio
import json
import logging
from typing import Callable, Literal

from pydantic import BaseModel

from dowse import Pipeline, logger
from dowse.impls.basic.effects import Printer
from dowse.interfaces import Classifier, Executor, Processor, SourceT

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


def get_ingredients_tool(food: str) -> str:
    # all tools should return a string

    if food == "hashbrowns":
        return json.dumps(["potatoes", "onions", "salt", "pepper"])
    elif food == "meatloaf":
        return json.dumps(["beef", "onions", "bread crumbs", "eggs"])
    elif food == "BLT":
        return json.dumps(["bacon", "lettuce", "tomato", "bread"])
    return "[]"


class ProcessedFood(BaseModel):
    name: str
    ingredients: list[str]


class GetIngredients(Processor[Food, ProcessedFood]):
    tools: list[Callable] = [
        get_ingredients_tool,
    ]

    async def to_string(self, command: Food) -> str:
        return command.model_dump_json()


class BreakfastJokeTopic(BaseModel):
    name: str
    ingredients: list[str]
    joke_topic: str


JokeTopicAdder = Processor[ProcessedFood, BreakfastJokeTopic](
    prompt=(
        "Update the JSON so the joke topic involves the hashbrowns losing a bet at the racetrack"
    ),
)


# we specify the input type, the processed type, and the output type
BreakfastExecutor = Executor[ProcessedFood, BreakfastJokeTopic, str](
    prompt="Write a joke about the breakfast food the user tells you",
    processors=[JokeTopicAdder],
)

LunchExecutor = Executor[ProcessedFood, ProcessedFood, str](
    prompt="Say something really serious, but mention the lunch food the user tells you.  Less than 100 words.",
)

DinnerExecutor = Executor[ProcessedFood, ProcessedFood, str](
    prompt="Say something really sad, but mention the dinner food the user tells you.  Less than 100 words.",
)


async def amain():
    pipeline = Pipeline[Food, Literal["breakfast", "lunch", "dinner"]](
        classifier=FoodClassifier,
        processors=[
            GetIngredients(),
        ],
        handlers={
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
