from typing import Literal

from emp_agents import AgentBase
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, Field

from .prompt import PROMPT
from .tools import (
    convert_decimal_eth_to_eth,
    convert_dollar_amount_to_eth,
    get_swap_output_tool,
    make_transfer_command,
)

swap_agent = AgentBase(
    prompt=PROMPT,
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


class SwapArgs(BaseModel):
    tokenIn: str
    tokenOut: str
    tokenInAddress: str
    tokenOutAddress: str
    amountIn: int
    amountOut: int
    slippage: float
    sender: str
    senderAddress: str
    recipient: str
    recipientAddress: str


class TransferArgs(BaseModel):
    token: str
    token_address: str
    amount: int
    recipient: str
    recipientAddress: str
    sender: str
    senderAddress: str


class CommandRequest(BaseModel):
    command: Literal["swap", "transfer"]
    args: SwapArgs | TransferArgs = Field(
        description="The arguments for the command, either swap args or transfer args",
    )


class CommandRequests(BaseModel):
    requests: list[CommandRequest]


async def get_commands(user_request: str) -> str:
    response = await swap_agent.answer(user_request, response_format=CommandRequests)
    return response
