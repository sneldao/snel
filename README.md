# dowse

<img src="https://raw.githubusercontent.com/empyrealapp/dowse/main/assets/logo.png" alt="dowse logo" width="300"/>

A powerful library for building natural language agents that can interpret and execute commands.

## Overview

Dowse is a Python library that enables you to build intelligent agents capable of:

- Parsing natural language commands and questions
- Classifying inputs into different types (e.g. commands vs questions)
- Executing structured commands based on natural language requests
- Responding to user queries with relevant information
- Building complex pipelines for command processing

## Key Features

- **Natural Language Processing**: Convert human language into structured commands
- **Flexible Pipeline Architecture**: Build custom processing flows with branching logic
- **Built-in Command Handlers**: Ready-to-use handlers for common operations
- **Extensible Design**: Easy to add new command types and handlers
- **Async Support**: Built for high-performance async/await operations


## Installation
```bash
# COMING SOON
pip install dowse
```


### Quickstart

```python
import asyncio
import os
import logging
from typing import Literal

from eth_rpc import set_alchemy_key

from dowse import Pipeline
from dowse.impls.basic.llms import BasicTweetClassifier, BasicTwitterCommands, BasicTwitterQuestion
from dowse.impls.basic.effects import Printer
from dowse.impls.basic.source import TwitterMock
from dowse.models import Tweet

logging.getLogger("dowse").setLevel(logging.DEBUG)
set_alchemy_key(os.environ["ALCHEMY_KEY"])


async def amain():
    # create a pipeline that classifiers commands as either a command or a question.
    pipeline = Pipeline[Tweet, Tweet, Literal["commands", "question"]](
        classifier=BasicTweetClassifier,
        # create a handler for each classification
        handlers={
            # commands are consumed by the BasicTwitterCommands operator
            "commands": BasicTwitterCommands.add_effect(Printer(prefix="COMMANDS")),
            # questions are consumed by the BasicTwitterQuestion operator
            "question": BasicTwitterQuestion.add_effects([Printer(prefix="QUESTION")]),
        },
        source=TwitterMock(),
    )

    result = await pipeline.process(
        # the input is a tweet, which then gets handled by the Pipeline
        Tweet(
            id=1684298214198108160,
            content="swap $300 for $UNI and then send half of it to @vitalikbuterin",
            creator_id=12,
            creator_name="@jack",
        ),
    )

    print(result)

    # run the pipeline for 3 executions, with a minimum of 120 seconds between each execution
    # this pulls data from the source and processes it
    await pipeline.run(max_executions=3, iteration_min_time=120)


if __name__ == "__main__":
    asyncio.run(amain())
```


### Tests

```bash
poetry install
poetry run pytest
```
