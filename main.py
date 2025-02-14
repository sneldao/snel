import asyncio

from src.impls import BasicContextHelper, BasicUserManager, ExecutorMock, TwitterMock
from src.runner import run


async def main():
    user_manager = BasicUserManager()
    executor = ExecutorMock(user_manager)
    context_helper = BasicContextHelper()
    twitter = TwitterMock()

    await run(twitter, executor, context_helper, max_executions=1)


if __name__ == "__main__":
    asyncio.run(main())
