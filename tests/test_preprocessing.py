import pytest

from dowse.impls.basic.llms.preprocessor import ProcessTokens
from dowse.models import Tweet
from dowse.tools import convert_dollar_amount_to_eth


@pytest.mark.asyncio()
async def test_pre_processor():
    formatted = await ProcessTokens().format(
        Tweet(
            id=1,
            content="swap $300 for AERO",
            creator_id=1,
            creator_name="test",
        )
    )
    eth_amount = await convert_dollar_amount_to_eth("$300")
    assert formatted.content.content == (
        f"swap {eth_amount} ETH (0x4200000000000000000000000000000000000006)"
        " for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)"
    )
    assert formatted.error_message is None


@pytest.mark.asyncio()
async def test_pre_processor_transfer():
    formatted = await ProcessTokens().format(
        Tweet(
            id=1,
            content="transfer $100 of ETH to @myfriend",
            creator_id=1,
            creator_name="test",
        )
    )
    eth_amount = await convert_dollar_amount_to_eth("$100")
    assert formatted.content.content == (
        f"transfer {eth_amount} ETH (0x4200000000000000000000000000000000000006)"
        " to @myfriend"
    )
    assert formatted.error_message is None


@pytest.mark.asyncio()
async def test_pre_processor_errors():
    formatted = await ProcessTokens().format(
        Tweet(
            id=1,
            content="swap $300 for NAFAJD",
            creator_id=1,
            creator_name="test",
        )
    )
    assert formatted.content is None
    assert formatted.error_message is not None
    assert "NAFAJD" in formatted.error_message
