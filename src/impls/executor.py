import json
from typing import Annotated

from typing_extensions import Doc

from ..interfaces import ExecutorT, SwapArgs, TransferArgs, UserManagerT
from ..tools import get_quote, get_token_address_tool


class ExecutorMock(ExecutorT):
    def __init__(self, user_manager: UserManagerT):
        self.user_manager = user_manager

    async def execute_swap(self, command: SwapArgs) -> None:
        """Execute a swap"""
        print("SWAPPING")

    async def execute_transfer(self, command: TransferArgs) -> None:
        """Execute a transfer"""
        print("TRANSFERRING")

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
        print(
            f"TOOL CALL: GET SWAP OUTPUT ({token_in}, {token_out}, {amount}, {slippage}, {chain_id}, {recipient})"
        )

        input_token = await get_token_address_tool(token_in)
        output_token = await get_token_address_tool(token_out)
        quotes = await get_quote(
            token_in=input_token,
            token_out=output_token,
            amount=amount,
            slippage=slippage,
            chain_id=chain_id,
            recipient=await self.user_manager.get_user_address(recipient),
        )

        if quotes.get("best"):
            best_quote = quotes["best"]
        else:
            best_quote = quotes

        if best_quote.get("message") == "Internal server error":
            raise ValueError(
                "you are probably hitting an API limit.  Retry or wait and try again"
            )
        return json.dumps(
            {
                "amountOut": str(int(best_quote["amountOut"])),
                "aggregator": best_quote["aggregator"],
                "inputToken": token_in,
                "inputTokenAddress": input_token,
                "outputToken": token_out,
                "outputTokenAddress": output_token,
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
        token_address = await get_token_address_tool(token)

        print(
            f"TOOL CALL: MAKE TRANSFER COMMAND ({token}, {amount}, {sender}, {recipient})"
        )

        return json.dumps(
            {
                "token": token,
                "tokenAddress": token_address,
                "to": recipient,
                "toAddress": await self.user_manager.get_user_address(recipient),
                "from": sender,
                "senderAddress": await self.user_manager.get_user_address(sender),
                "value": str(int(amount)),
            }
        )
