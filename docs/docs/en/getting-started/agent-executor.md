## AgentExecutor Class

The `AgentExecutor` class is a core component of the `dowse` library. It utilizes `emp_agents` to build LLM powered processing steps in an executionpipeline. It is designed to facilitate the execution of commands by processing inputs through a series of steps, including prompt generation, tool invocation, and result aggregation.

### Importing AgentExecutor

To use the `AgentExecutor` class, you need to import it from the `dowse` library. Here is an example of how to import the `AgentExecutor` class:

```python
from dowse import AgentExecutor
```

### Initializing AgentExecutor

The `AgentExecutor` class is initialized with a prompt, tools, and an executor. Here is an example of how to initialize the `AgentExecutor` class:

```python
agent_executor = AgentExecutor(
    prompt="You are a helpful assistant.",
    tools=[],
    executor=Executor(),
)
```

### Relative Imports

The `AgentExecutor` can import its prompt, tools, and executor from the relative files to the initialiation path of the executor.

If you structure your project like this:

```
dowse/
    __init__.py
    agent_executor.py
    PROMPT.txt
    tools.py
    examples.py
```

### Executing Commands

The `AgentExecutor` class is executed by calling the `execute` method. Here is an example of how to execute a command:

!!! tip
    The input/output type are used by as the response type
    when interacting with the Agent.  This forces
    the agent to respond in the desired type.


```python
from pydantic import BaseModel

from dowse import AgentExecutor
from dowse.models import AgentMessage

class InputType(BaseModel):
    name: str

class OutputType(BaseModel):
    age: int

executor = AgentExecutor[InputType, OutputType](
    prompt="Guess the person's age given their name."
)

output: AgentMessage[OutputType] = await executor.execute(InputType(name="John"))
```
