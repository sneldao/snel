import asyncio

from src.impls import BasicContextHelper, BasicUserManager, ExecutorMock, TwitterMock
from src.runner import run

content = """
@0xDeployer says: #simmi buy me $10 of $BNKR, swap half of it to $TN100x, and then send my $TN100x to @696_eth
 along with 0.0001 ETH for gas
"""


async def main():
    user_manager = BasicUserManager()
    executor = ExecutorMock(user_manager)
    context_helper = BasicContextHelper()
    twitter = TwitterMock()

    await run(twitter, executor, context_helper, max_executions=1)


if __name__ == "__main__":
    asyncio.run(main())
