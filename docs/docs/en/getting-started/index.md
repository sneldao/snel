# QUICK START

Install using pip

```bash
pip install dowse
```

## Basic Usage

`dowse` is a lightweight framework that abstracts the complexity around building an agent that ingests data sources, routes the command to the appropriate combination of prompts, tools and context, and executes the command and any side effects necessary.


```python
import asyncio
from datetime import datetime

from pydantic import BaseModel

from dowse import Executor, Processor
from dowse.models import AgentMessage


def get_current_time() -> str:
    """returns the current time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Note(BaseModel):
    """The base model for data ingested from a data source"""

    name: str
    content: str


class UserNote(BaseModel):
    """A note that contains user specific data"""

    name: str
    content: str
    fun_fact: str


class NoteSummary(BaseModel):
    """A psychological analysis of the user who wrote the note.  Relate it to his fun fact and how it might drive them to have this opinion"""

    summary: str
    recommendations: list[str]
    timestamp: str


class AddUserFact(Processor[Note, UserNote]):
    async def execute(self, note: Note) -> UserNote:
        if note.name == "John":
            return UserNote(
                fun_fact="John is a professional juggler who once juggled 17 rubber ducks while riding a unicycle backwards",
                **note.model_dump(),
            )
        elif note.name == "Alice":
            return UserNote(
                fun_fact="Alice is a quantum physicist who discovered three new particles while making her morning coffee",
                **note.model_dump(),
            )
        elif note.name == "Bob":
            return UserNote(
                fun_fact="Bob is a master chef who can taste a dish and instantly list all 47 ingredients used to make it",
                **note.model_dump(),
            )
        raise ValueError("No facts for user")


executor = Executor[
    Note,  # the input type of the first processor
    UserNote,  # type once all processors are run
    NoteSummary,  # the output type of the last processor
](
    processors=[
        AddUserFact(),
    ],
    prompt="""
        You are a helpful assistant that receives notes, and you will respond by analyzing the note and
        how it relates to the user's fun fact.

        Make sure to timestamp and log your response.
    """,
    tools=[
        get_current_time,
    ],
)


async def amain() -> None:
    response: AgentMessage[NoteSummary] = await executor.execute(
        Note(
            name="John",
            content="I can't keep up with all these things in flight.  It makes me feel loco!!!",
        )
    )
    assert (
        response.content is not None
    ), "this should not error because John is in the user data"

    print("TIMESTAMP:", response.content.timestamp)
    print("SUMMARY:", response.content.summary)

    print("RECOMMENDATIONS:")
    for recommendation in response.content.recommendations:
        print("\t- ", recommendation)


asyncio.run(amain())
```

And when we run this we get back something like:

```text
TIMESTAMP: 2025-02-18 04:12:10
SUMMARY: John is probably a person who likes to challenge himself with tasks that require high levels of concentration and multitasking, as evidenced by his ability to juggle 17 rubber ducks while riding a unicycle backwards. This note suggests he might be feeling overwhelmed or stressed by the number of things he has to manage, possibly because they lack the structured environment similar to his juggling act. Juggling, in a metaphorical sense, might be easier for John because it has defined edges and patterns, unlike chaotic and unpredictable real-life events.
RECOMMENDATIONS:
        -  Apply structured approaches to task management, such as using a priority matrix or checklist.
        -  Relate the tasks to juggling by visualizing managing them like juggling items, focusing on maintaining rhythm and balance.
        -  Take regular breaks to help reset and clear the mind, just like a juggler does between performances.
        -  Simplify tasks into smaller, manageable components, akin to juggling fewer items first.
```
