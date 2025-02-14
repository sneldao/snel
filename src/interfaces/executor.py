from abc import ABC, abstractmethod
from typing import Annotated, Literal, cast

from pydantic import BaseModel, Field
from typing_extensions import Doc


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


class Command(BaseModel):
    command: Literal["swap", "transfer"]
    args: SwapArgs | TransferArgs = Field(
        description="The arguments for the command, either swap args or transfer args",
    )


class ExecutorT(ABC):
    async def execute_command(self, command: Command) -> None:
        if command.command == "swap":
            swap_args = cast(SwapArgs, command.args)
            await self.execute_swap(swap_args)
        elif command.command == "transfer":
            transfer_args = cast(TransferArgs, command.args)
            await self.execute_transfer(transfer_args)

    @abstractmethod
    async def execute_swap(self, command: SwapArgs) -> None:
        """Execute a swap"""

    @abstractmethod
    async def execute_transfer(self, command: TransferArgs) -> None:
        """Execute a transfer"""

    @abstractmethod
    async def get_swap_output_tool(
        self,
        token_in: Annotated[
            str,
            Doc(
                "The token to swap from.  Must be a token symbol, token address, or ETH."
            ),
        ],
        token_out: Annotated[
            str, Doc("The token to swap to.  Must be a token symbol or ETH")
        ],
        amount: Annotated[int, Doc("The amount to swap")],
        recipient: Annotated[
            str,
            Doc(
                "The recipient of the swap.  Can be a twitter username or an ethereum address.  If it starts with @ it's a username, don't add 0x to the front of it"
            ),
        ],
        slippage: Annotated[float, Doc("The slippage tolerance")] = 1,
        chain_id: Annotated[int, Doc("The chain id")] = 8453,
    ) -> str:
        """Gets the swap output command as a string"""

    @abstractmethod
    async def make_transfer_command(
        self,
        token: Annotated[str, Doc("The token to transfer")],
        amount: Annotated[int, Doc("The amount to transfer")],
        sender: Annotated[str, Doc("The sender of the transfer")],
        recipient: Annotated[str, Doc("The recipient of the transfer")],
    ) -> str:
        """Create a transfer command, returning the output that would be used to make the transfer"""

    @abstractmethod
    async def get_user_address_helper(
        self,
        username: Annotated[str, Doc("The username to get the address for")],
    ) -> str:
        """Get the address for a username"""
