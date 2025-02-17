from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel

from dowse.interfaces.executor import Executor
from dowse.models import Tweet


class Response(BaseModel):
    response: str


BasicTwitterQuestion = Executor[Tweet, Tweet, Response](
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
)
