from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel

from dowse.interfaces.executor import Executor
from dowse.models import Tweet

from ...tools import CommandRequest, Tools
from ..preprocessor import FormattedCommand, ProcessTokens
from .examples import EXAMPLES


class CommandsList(BaseModel):
    commands: list[CommandRequest]


BasicTwitterCommands = Executor[Tweet, FormattedCommand, CommandsList](
    prompt="",
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
    preprocessors=[
        ProcessTokens(),
    ],
    tools=Tools.tools(),
    examples=EXAMPLES,
)
