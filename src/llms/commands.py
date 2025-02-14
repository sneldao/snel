from typing import Literal

from emp_agents import AgentBase
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, Field

from ..interfaces import ExecutorT, SwapArgs, TransferArgs
from ..prompts import COMMANDS_PROMPT
from ..tools import (
    convert_decimal_eth_to_eth,
    convert_dollar_amount_to_eth,
    get_swap_output_tool,
    make_transfer_command,
)

swap_agent = AgentBase(
    prompt=COMMANDS_PROMPT,
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
    tools=[
        get_swap_output_tool,
        make_transfer_command,
        convert_dollar_amount_to_eth,
        convert_decimal_eth_to_eth,
    ],
)


class CommandRequest(BaseModel):
    command: Literal["swap", "transfer"]
    args: SwapArgs | TransferArgs = Field(
        description="The arguments for the command, either swap args or transfer args",
    )


class CommandRequests(BaseModel):
    requests: list[CommandRequest]


async def get_commands(user_request: str, executor: ExecutorT) -> CommandRequests:
    swap_agent = AgentBase(
        prompt=COMMANDS_PROMPT,
        provider=OpenAIProvider(
            default_model=OpenAIModelType.gpt4o,
        ),
        tools=[
            executor.get_swap_output_tool,
            executor.make_transfer_command,
            convert_dollar_amount_to_eth,
            convert_decimal_eth_to_eth,
        ],
    )
    response = await swap_agent.answer(user_request, response_format=CommandRequests)
    print("response", response)
    return CommandRequests.model_validate_json(response)
