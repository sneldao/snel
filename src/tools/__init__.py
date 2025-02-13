import json
from typing import Annotated

from eth_rpc.utils import to_checksum
from eth_typeshed.chainlink.eth_usd_feed import ChainlinkPriceOracle, ETHUSDPriceFeed
from eth_typing import ChecksumAddress
from typing_extensions import Doc

from .aggregator import get_quote
from .simulacrum import get_user_address
from .symbol_to_address import get_token_for_symbol
from .twitter import get_user_id


def is_address(address: str) -> bool:
    return len(address) == 42 and address.startswith("0x")


async def get_token_address_tool(
    symbol_or_token_address: Annotated[
        str, Doc("The symbol of the token to get the address for")
    ],
) -> ChecksumAddress:
    """
    get the address for a given symbol
    """

    symbol_or_token_address = symbol_or_token_address.lstrip("$")

    if is_address(symbol_or_token_address):
        return to_checksum(symbol_or_token_address)
    if symbol_or_token_address.lower() == "eth":
        return to_checksum("0x4200000000000000000000000000000000000006")

    if symbol_or_token_address[0] == "@":
        user_id = await get_user_id(symbol_or_token_address)
        assert user_id is not None
        return await get_user_address(user_id)

    return to_checksum(await get_token_for_symbol(symbol_or_token_address))


async def get_swap_output_tool(
    token_in: Annotated[
        str,
        Doc("The token to swap from.  Must be a token symbol, token address, or ETH."),
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
    """
    create a swap, and return the token in, token out, amount and dex aggregator that would be used to make the swap
    """

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
        recipient=await get_user_address_helper(recipient),
    )

    if quotes.get("best"):
        best_quote = quotes["best"]
    else:
        best_quote = quotes

    print(best_quote)
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
    token: Annotated[str, Doc("The token to transfer")],
    amount: Annotated[int, Doc("The amount to transfer")],
    sender: Annotated[str, Doc("The sender of the transfer")],
    recipient: Annotated[str, Doc("The recipient of the transfer")],
) -> str:
    """
    create a transfer, and return the output and dex aggregator that would be used to make the transfer
    """

    token_address = await get_token_address_tool(token)

    print(
        f"TOOL CALL: MAKE TRANSFER COMMAND ({token}, {amount}, {sender}, {recipient})"
    )

    return json.dumps(
        {
            "token": token,
            "tokenAddress": token_address,
            "to": recipient,
            "toAddress": await get_user_address_helper(recipient),
            "from": sender,
            "senderAddress": await get_user_address_helper(sender),
            "value": str(int(amount)),
        }
    )


async def get_user_address_helper(
    username: Annotated[str, Doc("The username to get the address for")],
) -> ChecksumAddress:
    """
    get the address for a given username.  If the user starts with @ or is clearly a person receiving the transfer, use this.
    """
    if is_address(username):
        return to_checksum(username)

    user_id = await get_user_id(username)
    assert user_id is not None
    return await get_user_address(user_id)


async def get_eth_price() -> float:
    """
    get the price of ETH in USD
    """

    eth_usd_feed = ETHUSDPriceFeed(address=ChainlinkPriceOracle.Ethereum.ETH)
    latest_round_data = await eth_usd_feed.latest_round_data().get()
    return latest_round_data.answer / 1e8


async def convert_dollar_amount_to_eth(
    amount: Annotated[str, Doc("The dollar amount to convert to ETH")]
) -> str:
    """
    convert a dollar amount to ETH
    """

    print(f"TOOL CALL: CONVERT DOLLAR AMOUNT TO ETH ({amount})")

    eth_price = await get_eth_price()
    dollar_amount = float(amount.strip("$"))
    return str(int(dollar_amount / eth_price * 1e18))


def convert_decimal_eth_to_eth(amount: str) -> str:
    """
    convert a decimal ETH amount to a string ETH amount
    """
    return str(int(float(amount) * 1e18))
