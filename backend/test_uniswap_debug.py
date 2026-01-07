import asyncio
import logging
from decimal import Decimal
from app.protocols.uniswap_adapter import UniswapAdapter
from app.models.token import TokenInfo

async def main():
    logging.basicConfig(level=logging.DEBUG)
    adapter = UniswapAdapter()
    
    usdc_token = TokenInfo(
        id="usdc",
        name="USD Coin",
        symbol="USDC",
        decimals=6,
        type="erc20",
        verified=True,
        addresses={8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}
    )
    
    weth_token = TokenInfo(
        id="weth",
        name="Wrapped Ether",
        symbol="WETH",
        decimals=18,
        type="erc20",
        verified=True,
        addresses={8453: "0x4200000000000000000000000000000000000006"}
    )
    
    print("Testing Uniswap quote...")
    quote = await adapter.get_quote(
        from_token=usdc_token,
        to_token=weth_token,
        amount=Decimal("1"),
        chain_id=8453,
        wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    )
    print(f"Quote result: {quote}")

if __name__ == "__main__":
    asyncio.run(main())
