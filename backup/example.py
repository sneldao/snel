import asyncio
import os
import logging
from enum import StrEnum
from typing import Literal
from pathlib import Path

from eth_rpc import set_alchemy_key
from dotenv import load_dotenv

from dowse import Pipeline
from dowse.impls.basic.llms import BasicTweetClassifier, BasicTwitterCommands, BasicTwitterQuestion
from dowse.impls.basic.effects import Printer
from dowse.impls.basic.source import TwitterMock
from dowse.models import Tweet

# Load environment variables
env_path = Path('.env').absolute()
if not env_path.exists():
    raise FileNotFoundError(f"Could not find .env file at {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# Debug prints
print("Environment variables loaded from:", env_path)
print("ALCHEMY_KEY:", os.getenv("ALCHEMY_KEY"))
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
print("QUICKNODE_ENDPOINT:", os.getenv("QUICKNODE_ENDPOINT"))

# Set up logging
logging.getLogger("dowse").setLevel(logging.DEBUG)

# Ensure all required environment variables are in os.environ
required_vars = {
    "ALCHEMY_KEY": os.getenv("ALCHEMY_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "QUICKNODE_ENDPOINT": os.getenv("QUICKNODE_ENDPOINT")
}

for var_name, value in required_vars.items():
    if not value:
        raise ValueError(f"{var_name} environment variable is required")
    os.environ[var_name] = value

# Set Alchemy key
set_alchemy_key(required_vars["ALCHEMY_KEY"])


class Classifications(StrEnum):
    """A class that defines the different classifications that can be made by the pipeline."""
    COMMANDS = "commands"
    QUESTION = "question"


async def amain():
    # create a pipeline that classifies commands as either a command or a question
    pipeline = Pipeline[Tweet, Tweet, Classifications](
        # classifies the request as one of the Classifications
        classifier=BasicTweetClassifier,
        # a handler that executes each classification
        handlers={
            # commands are consumed by the BasicTwitterCommands operator
            "commands": BasicTwitterCommands.add_effect(Printer(prefix="COMMANDS")),
            # questions are consumed by the BasicTwitterQuestion operator
            "question": BasicTwitterQuestion.add_effects([Printer(prefix="QUESTION")]),
        },
        # the source that will emit the data that is consumed by the pipeline
        source=TwitterMock(),
    )

    # process a single event
    result = await pipeline.process(
        # the input is a tweet, which then gets handled by the Pipeline
        Tweet(
            id=1684298214198108160,
            content="swap $300 for $UNI and then send half of it to @papajamsbuterin",
            creator_id=12,
            creator_name="@jack",
        ),
    )
    print("Process result:", result)


if __name__ == "__main__":
    asyncio.run(amain()) 