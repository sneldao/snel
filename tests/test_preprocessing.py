import pytest

from dowse.impls.basic.llms.preprocessor import process_tokens
from dowse.models import Tweet

# from dowse.tools import convert_dollar_amount_to_eth


@pytest.mark.asyncio()
async def test_pre_processor():
    formatted = await process_tokens.process(
        Tweet(
            id=1,
            content="swap $300 for AERO and send 50% of the output to @user2",
            creator_id=1,
            creator_name="test",
        )
    )

    # eth_amount = await convert_dollar_amount_to_eth("$300")
    # assert (
    #     formatted.content.content.lower().strip().rstrip(".")
    #     == (
    #         f"1. swap {eth_amount} (0x4200000000000000000000000000000000000006) for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)\n"  # noqa: E501
    #         "2. send 50% of the output to @user2"
    #     ).lower()
    # )
    assert formatted.content.content
    assert formatted.error_message is None


@pytest.mark.asyncio()
async def test_pre_processor_transfer():
    formatted = await process_tokens.process(
        Tweet(
            id=1,
            content="transfer $100 of ETH to @myfriend",
            creator_id=1,
            creator_name="test",
        )
    )

    # eth_amount = await convert_dollar_amount_to_eth("$100")
    # assert (
    #     formatted.content.content.lower()
    #     == (
    #         f"1. transfer {eth_amount} (0x4200000000000000000000000000000000000006)"
    #         " to @myfriend"
    #     ).lower()
    # )
    assert formatted.content.content
    assert formatted.error_message is None


@pytest.mark.asyncio()
async def test_pre_processor_errors():
    formatted = await process_tokens.process(
        Tweet(
            id=1,
            content="swap $300 for NAFAJD",
            creator_id=1,
            creator_name="test",
        )
    )

    assert formatted.error_message is not None
    assert "NAFAJD" in formatted.error_message
