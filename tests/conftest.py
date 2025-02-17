import os

import pytest
from eth_rpc import set_alchemy_key


@pytest.fixture(scope="session", autouse=True)
def setup_tests():
    """Create a test runner instance with mock components."""
    set_alchemy_key(os.getenv("ALCHEMY_KEY"))
