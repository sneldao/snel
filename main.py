import asyncio

from src.llm import get_commands

command = """
@0xDeployer says: #simmi buy me $10 of $BNKR, swap half of it to $TN100x, and then send my $TN100x to @696_eth
 along with 0.0001 ETH for gas
"""


async def main():
    commands = await get_commands(command)
    print(commands)


if __name__ == "__main__":
    asyncio.run(main())
