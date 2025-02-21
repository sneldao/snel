### Examples


## Example: Using dowse with emp-agents

Here is an example of how to use the `dowse` library with `emp-agents` to create an intelligent agent that processes user notes and provides psychological analysis based on user-specific data. The `emp-agents` library is used to simulate user and assistant messages, which can be processed by the `dowse` pipeline to generate appropriate responses.

```python
from emp_agents import UserMessage, AssistantMessage

examples = [[
    UserMessage(content="Hello, how are you?"),
    AssistantMessage(content="I'm doing well, thank you for asking!"),
    UserMessage(content="What is the weather in Tokyo?"),
    AssistantMessage(content="The weather in Tokyo is sunny and warm."),
]]
```
