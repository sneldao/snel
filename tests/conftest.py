import asyncio
import logging
import os

import pytest
from eth_rpc import set_alchemy_key

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
async def setup_tests():
    """Create a test runner instance with mock components."""
    set_alchemy_key(os.getenv("ALCHEMY_KEY"))
    logging.getLogger("dowse").setLevel(logging.DEBUG)


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()
