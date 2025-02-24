from dowse.models import Tweet
import asyncio
import logging
from typing import Literal, Optional
import os
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SwapCommand(BaseModel):
    """A command to swap tokens."""
    action: Literal["swap", "price", "unknown"]
    amount: Optional[float] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None

class SwapCommandParser:
    """Parser for swap commands."""
    def parse(self, content: str) -> SwapCommand:
        content = content.lower()
        try:
            # Handle swap commands
            if "swap" in content:
                words = content.split()
                amount_idx = words.index("swap") + 1
                amount = float(words[amount_idx])
                token_in = words[amount_idx + 1].upper()
                token_out = words[words.index("for") + 1].upper()
                return SwapCommand(
                    action="swap",
                    amount=amount,
                    token_in=token_in,
                    token_out=token_out
                )
            # Handle buy commands
            elif "buy" in content:
                words = content.split()
                amount_idx = words.index("buy") + 1
                amount = float(words[amount_idx])
                token_out = words[amount_idx + 1].upper()
                token_in = "ETH"  # Default to ETH for buy commands
                return SwapCommand(
                    action="swap",
                    amount=amount,
                    token_in=token_in,
                    token_out=token_out
                )
            # Handle price queries
            elif "price" in content:
                words = content.split()
                if "eth" in content:
                    token = "ETH"
                elif "usdc" in content:
                    token = "USDC"
                else:
                    token = None
                return SwapCommand(
                    action="price",
                    token_in=token
                )
            # Unknown commands
            else:
                return SwapCommand(action="unknown")
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse command: {e}")
            return SwapCommand(action="unknown")

class SwapExecutor:
    """Executes swap commands."""
    async def execute(self, command: SwapCommand) -> str:
        if command.action == "swap":
            return f"Swapping {command.amount} {command.token_in} for {command.token_out}"
        elif command.action == "price":
            if command.token_in:
                return f"Getting price for {command.token_in}"
            else:
                return "Please specify which token you want the price for"
        else:
            return "I don't understand that command. Try something like 'swap 1 ETH for USDC' or 'what's the price of ETH?'"

async def test_swap_commands():
    parser = SwapCommandParser()
    executor = SwapExecutor()
    
    # Test different command formats
    test_commands = [
        "swap 1 ETH for USDC",
        "buy 2 USDC with ETH",
        "what is the price of ETH",
        "hello world"  # Unknown command
    ]
    
    for cmd in test_commands:
        logger.info(f"\nTesting command: {cmd}")
        try:
            # Parse the command
            parsed = parser.parse(cmd)
            logger.info(f"Parsed command: {parsed}")
            
            # Execute the command
            result = await executor.execute(parsed)
            logger.info(f"Result: {result}")
        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)

if __name__ == "__main__":
    print("\nTesting Swap Commands...")
    asyncio.run(test_swap_commands()) 