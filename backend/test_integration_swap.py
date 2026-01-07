import asyncio
import logging
import sys
import os
from decimal import Decimal

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.swap_service import swap_service

async def test_integration():
    logging.basicConfig(level=logging.INFO)
    print("Testing high-level swap_service integration for Uniswap V3 (Base)...")
    
    # Try USDC -> WETH on Base (8453)
    quote = await swap_service.get_quote(
        from_token_id="usdc",
        to_token_id="weth",
        amount=Decimal("1.0"),
        chain_id=8453,
        wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    )
    
    print(f"Integration Quote Success: {quote.get('success')}")
    if quote.get("success"):
        print(f"Protocol used: {quote.get('protocol')}")
        print(f"To amount: {quote.get('to_amount')} WETH")
    else:
        print(f"Error: {quote.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_integration())
