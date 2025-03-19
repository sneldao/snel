from app.utils.providers import OpenAIModelType, OpenAIProvider  # Updated from emp_agents
from pydantic import BaseModel

from dowse.interfaces import AgentExecutor

from ...tools import CommandRequest, Tools
from ..preprocessor import FormattedCommand, process_tokens


class CommandsList(BaseModel):
    commands: list[CommandRequest]


BasicTwitterCommands = process_tokens >> AgentExecutor[FormattedCommand, CommandsList](
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
    tools=[
        Tools.get_amount_out_tool,
        Tools.get_percentage,
    ],
)
