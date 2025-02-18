import asyncio
import logging
import os

import pytest
from eth_rpc import set_alchemy_key


@pytest.fixture(autouse=True)
async def setup_tests():
    """Create a test runner instance with mock components."""
    set_alchemy_key(os.getenv("ALCHEMY_KEY"))
    logging.getLogger("dowse").setLevel(logging.DEBUG)


@pytest.fixture(scope="session")
def event_loop(request):
    """
    Redefine the event loop to support session/module-scoped fixtures;
    see https://github.com/pytest-dev/pytest-asyncio/issues/68
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()

    try:
        yield loop
    finally:
        loop.close()
