# Dowse Pointless

<p align="center">
  <a href="https://dowse.empyrealsdk.com"><img src="https://raw.githubusercontent.com/empyrealapp/dowse/main/assets/logo.png" alt="dowse" height=300></a>
</p>
<p align="center">
    <em>dowse, a python library for building natural language agents that can interpret and execute commands.</em>
</p>
<p align="center">
<a href="https://github.com/empyrealapp/dowse/actions?query=event%3Apush+branch%3Amain" target="_blank">
    <img src="https://github.com/empyrealapp/dowse/actions/workflows/publish.yaml/badge.svg?event=push&branch=main" alt="Test">
</a>
<!-- <a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/empyrealapp/dowse" target="_blank">
    <img src="https://coverage-badge.samuelcolvin.workers.dev/empyrealapp/dowse.svg" alt="Coverage">
</a> -->
<a href="https://pypi.org/project/dowse" target="_blank">
    <img src="https://img.shields.io/pypi/v/dowse?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/dowse" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/dowse.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

---

**Documentation**: <a href="https://dowse.empyrealsdk.com" target="_blank">https://dowse.empyrealsdk.com</a>

**Source Code**: <a href="https://github.com/empyrealapp/dowse" target="_blank">https://github.com/empyrealapp/dowse</a>

---

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

## Project Structure

```
dowse-pointless/
├── api.py              # FastAPI backend server
├── frontend/          # Next.js frontend application
├── .env              # Environment variables
└── README.md         # This file
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- Poetry (Python package manager)
- npm or yarn (Node.js package manager)

### Environment Setup

1. Create a `.env` file in the root directory with the following variables:

```bash
ALCHEMY_KEY=your_alchemy_key
OPENAI_API_KEY=your_openai_key
QUICKNODE_ENDPOINT=your_quicknode_endpoint
```

### Backend Setup

1. Install Python dependencies:

```bash
poetry install
```

2. Start the backend server:

```bash
poetry run uvicorn api:app --reload
```

The backend will be available at `http://localhost:8000`.

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install Node.js dependencies:

```bash
npm install
# or
yarn install
```

3. Start the development server:

```bash
npm run dev
# or
yarn dev
```

The frontend will be available at `http://localhost:3000`.

## Development

### Running Tests

```bash
poetry install
poetry run pytest
```

### Git Best Practices

When committing changes:

1. Check untracked files before committing:

```bash
git clean -n
```

2. Review changes to be committed:

```bash
git status
```

3. Avoid committing build files and dependencies:

- Use `.gitignore` to exclude build directories
- Don't commit `node_modules/` or `.next/` directories
- Don't commit environment files (`.env`)

## Requirements

dowse is built utilizing the following libraries:

- <a href="https://docs.pydantic.dev/" class="external-link" target="_blank">Pydantic</a> for the data parts
- <a href="https://github.com/empyrealapp/eth-rpc" class="external-link" target="_blank">eth-rpc</a> for the blockchain parts
- <a href="https://github.com/empyrealapp/emp-agents" class="external-link" target="_blank">emp-agents</a> for the agent parts

## Example Usage

The following example shows how to create a pipeline that classifies tweets as either a command or a question:

```python
import asyncio
import os
import logging
from enum import StrEnum
from typing import Literal

from eth_rpc import set_alchemy_key

from dowse import Pipeline
from dowse.impls.basic.llms import BasicTweetClassifier, BasicTwitterCommands, BasicTwitterQuestion
from dowse.impls.basic.effects import Printer
from dowse.impls.basic.source import TwitterMock
from dowse.models import Tweet

logging.getLogger("dowse").setLevel(logging.DEBUG)
set_alchemy_key(os.environ["ALCHEMY_KEY"])


class Classifications(StrEnum):
    """A class that defines the different classifications that can be made by the pipeline."""
    COMMANDS = "commands"
    QUESTION = "question"


async def amain():
    pipeline = Pipeline[Tweet, Tweet, Classifications](
        classifier=BasicTweetClassifier,
        handlers={
            "commands": BasicTwitterCommands.add_effect(Printer(prefix="COMMANDS")),
            "question": BasicTwitterQuestion.add_effects([Printer(prefix="QUESTION")]),
        },
        source=TwitterMock(),
    )

    result = await pipeline.process(
        Tweet(
            id=1684298214198108160,
            content="swap $300 for $UNI and then send half of it to @vitalikbuterin",
            creator_id=12,
            creator_name="@jack",
        ),
    )

    await pipeline.run(max_executions=3, iteration_min_time=120)


if __name__ == "__main__":
    asyncio.run(amain())
```
