### The Executor Class

The `Executor` class is the base class for executing actions on data as part of a pipeline.

### Importing the Executor Class

To use the `Executor` class, you need to import it from the `dowse` library. Here is an example of how to import the `Executor` class:

```python
from dowse import Executor
```

### Initializing the Executor Class

The `Executor` class is initialized with a prompt, tools, and an executor. Here is an example of how to initialize the `Executor` class:

```python
class MyExecutor(Executor[int, str]):
    async def execute(self, input_: int) -> str:
        return f"The input is {input_}"
```
