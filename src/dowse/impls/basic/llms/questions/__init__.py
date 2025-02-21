from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel

from dowse.interfaces.executor import ExecutorWithProcessors
from dowse.models import Tweet


class Response(BaseModel):
    response: str


BasicTwitterQuestion = ExecutorWithProcessors[Tweet, Tweet, Response](
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
)
