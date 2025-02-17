from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel

from dowse.interfaces.executor import Executor
from dowse.models import Tweet

from ...tools import CommandRequest, Tools
from ..preprocessor import FormattedCommand, token_processor


class CommandsList(BaseModel):
    commands: list[CommandRequest]


BasicTwitterCommands = Executor[Tweet, FormattedCommand, CommandsList](
    prompt="",
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
    preprocessors=[token_processor],
    tools=Tools.tools(),
)
