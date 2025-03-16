import pytest

from dowse.impls.basic.llms import BasicTwitterCommands as parser
from dowse.models import Tweet
from dowse.models.commands import SwapArgs, TransferArgs
from dowse.tools import convert_dollar_amount_to_eth


@pytest.mark.asyncio()
# @pytest.mark.skip(reason="This is no longer an essential test")
async def test_transfer():
    commands = await parser.execute(
        Tweet(
            id=1890118705016877145,
            content="transfer $10 of ETH to @papajamsButerin",
            creator_id=1414021381298089984,
            creator_name="@ethereum",
        ),
    )
    assert commands.error_message is None
    assert len(commands.content.commands) == 1

    command = commands.content.commands[0]

    assert command.command == "transfer"
    assert isinstance(command.args, TransferArgs)

    assert command.args.token_address == "0x4200000000000000000000000000000000000006"

    # NOTE: if ETH price moves a lot (up or down) this will fail
    eth_amount = float((await convert_dollar_amount_to_eth("10")).split(" ")[0])
    assert command.args.amount > eth_amount * 0.97
    assert command.args.amount < eth_amount * 1.03

    assert command.args.recipient == "@papajamsButerin"


@pytest.mark.asyncio()
@pytest.mark.skip(reason="This is no longer an essential test")
async def test_swap():
    commands = await parser.execute(
        Tweet(
            id=1890118705016877145,
            content="swap $300 for cbBTC",
            creator_id=1414021381298089984,
            creator_name="@ethereum",
        ),
    )

    assert len(commands.content.commands) == 1
    command = commands.content.commands[0]

    assert command.command == "swap"
    assert isinstance(command.args, SwapArgs)

    command_args = command.args
    assert command_args.token_in_address == "0x4200000000000000000000000000000000000006"
    assert (
        command_args.token_out_address == "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
    )
    assert command_args.amount_in > 9e16
    assert command_args.amount_in < 2e17
    assert command_args.recipient == "@ethereum"


@pytest.mark.asyncio()
async def test_swap_error():
    commands = await parser.execute(
        Tweet(
            id=1890118705016877145,
            content="swap $300 for XJAJKF",
            creator_id=1414021381298089984,
            creator_name="@user",
        ),
    )
    assert commands.content is None
    error_reason = commands.error_message
    assert error_reason is not None
    assert "XJAJKF" in error_reason


@pytest.mark.asyncio()
async def test_swap_error_2():
    commands = await parser.execute(
        Tweet(
            id=1890118705016877145,
            content="swap $300 for DOGEEE",
            creator_id=1414021381298089984,
            creator_name="@user",
        ),
    )

    error_reason = commands.error_message
    assert error_reason is not None
    assert "DOGEEE" in error_reason
