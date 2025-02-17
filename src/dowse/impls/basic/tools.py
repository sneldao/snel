import json
from typing import Annotated, Callable, Literal, cast

from eth_rpc.utils import to_checksum
from pydantic import BaseModel, Field
from typing_extensions import Doc

from dowse.interfaces import UserManagerT
from dowse.logger import logger
from dowse.models.commands import SwapArgs, TransferArgs
from dowse.tools import convert_decimal_eth_to_wei, get_token_address_tool
from dowse.tools.best_route.kyber import Quote
from dowse.tools.best_route.kyber import get_quote as get_kyber_quote

from .user import BasicUserManager


class CommandRequest(BaseModel):
    command: Literal["swap", "transfer"]
    args: SwapArgs | TransferArgs = Field(
        description="The arguments for the command, either swap args or transfer args",
    )


class CommandTools(BaseModel):
    username_to_address: dict[str, str] = Field(default_factory=dict)
    user_manager: UserManagerT = Field(default_factory=BasicUserManager)

    async def execute_command(self, command: CommandRequest) -> None:
        if command.command == "swap":
            swap_args = cast(SwapArgs, command.args)
            await self.execute_swap(swap_args)
        elif command.command == "transfer":
            transfer_args = cast(TransferArgs, command.args)
            await self.execute_transfer(transfer_args)

    async def make_swap_command(
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
                "The recipient of the swap.  Can be a twitter username or an ethereum address.  "
                "If it starts with @ it's a username, don't add 0x to the front of it"
            ),
        ],
        chain_id: Annotated[int, Doc("The chain id")] = 8453,
    ) -> str:
        """Convert the swap arguments to the structured syntax for a swap"""
        slippage = 1
        logger.debug(
            "Tool Call: make_swap_command (%s, %s, %s, %s, %s, %s)",
            token_in,
            token_out,
            amount,
            slippage,
            chain_id,
            recipient,
        )

        input_token = await get_token_address_tool(token_in)
        output_token = await get_token_address_tool(token_out)

        chain_id = cast(Literal[1, 8453, 42161, 10, 137, 43114], chain_id)
        quote: Quote = await get_kyber_quote(
            token_in=to_checksum(input_token),
            token_out=to_checksum(output_token),
            amount=amount,
            chain_id=chain_id,
        )

        return json.dumps(
            {
                "amount_out": str(int(quote.amount_out)),
                "aggregator": quote.aggregator,
                "input_token_symbol": token_in,
                "input_token_address": input_token,
                "output_token_symbol": token_out,
                "output_token_address": output_token,
            }
        )

    async def make_transfer_command(
        self,
        token: Annotated[str, Doc("The token to transfer")],
        amount: Annotated[int, Doc("The amount to transfer")],
        sender: Annotated[str, Doc("The sender of the transfer")],
        recipient: Annotated[str, Doc("The recipient of the transfer")],
    ) -> str:
        """Create a transfer command, returning the output that would be used to make the transfer"""
        logger.debug(
            f"Tool Call: make_transfer_command ({token}, {amount}, {sender}, {recipient})"
        )

        token_address = await get_token_address_tool(token)
        return json.dumps(
            {
                "token_symbol": token,
                "token_address": token_address,
                "sender": sender,
                "recipient": recipient,
                "value": str(int(amount)),
            }
        )

    async def get_user_address_helper(
        self,
        username: Annotated[str, Doc("The username to get the address for")],
    ) -> str:
        """Get the address for a username"""
        if not self.username_to_address.get(username):
            address = await self.user_manager.get_user_address(username)
            self.username_to_address[username] = address
        return self.username_to_address[username]

    async def execute_swap(self, command: SwapArgs) -> None:
        """Execute a swap"""
        raise NotImplementedError("Swap not implemented")

    async def execute_transfer(self, command: TransferArgs) -> None:
        """Execute a transfer"""
        raise NotImplementedError("Transfer not implemented")

    def tools(self) -> list[Callable]:
        return [
            convert_decimal_eth_to_wei,
            self.make_swap_command,
            self.make_transfer_command,
        ]


Tools = CommandTools()
