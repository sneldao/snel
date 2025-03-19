from app.utils.providers import OpenAIModelType, OpenAIProvider  # Updated from emp_agents
from pydantic import BaseModel

from dowse.interfaces.executor import AgentExecutor
from dowse.models import Tweet


class Response(BaseModel):
    response: str


BasicTwitterQuestion = AgentExecutor[Tweet, Response](
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
)
