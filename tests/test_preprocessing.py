import pytest

from dowse.impls.basic.llms.preprocessor import token_processor
from dowse.models import Tweet
from dowse.tools import convert_dollar_amount_to_eth


@pytest.mark.asyncio(loop_scope="session")
async def test_pre_processor():
    formatted = await token_processor.format(
        Tweet(
            id=1,
            content="swap $300 for AERO",
            creator_id=1,
            creator_name="test",
        )
    )
    eth_amount = await convert_dollar_amount_to_eth("$300")
    assert formatted.content.user_request == (
        f"swap {eth_amount} ETH (0x4200000000000000000000000000000000000006)"
        " for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)"
    )
    assert formatted.error_message is None


@pytest.mark.asyncio(loop_scope="session")
async def test_pre_processor_errors():
    formatted = await token_processor.format(
        Tweet(
            id=1,
            content="swap $300 for DFKJALF",
            creator_id=1,
            creator_name="test",
        )
    )
    assert formatted.content is None
    assert formatted.error_message is not None
    assert "DFKJALF" in formatted.error_message
