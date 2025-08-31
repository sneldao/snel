"""
Skeleton test suite for Uniswap v3 integration.
Targets:
- Fee tier selection (500/3000/10000)
- Quote correctness and tx simulation consistency
- Permit2 path included when allowance-limited
- Error handling for unsupported chain/token and invalid inputs
"""
import asyncio
import pytest
from decimal import Decimal

from app.protocols.uniswap_adapter import UniswapAdapter
from app.models.token import TokenInfo


@pytest.mark.asyncio
async def test_smoke_quote_and_tx_build_base_usdc_weth():
    adapter = UniswapAdapter()
    quote = await adapter.get_quote(
        from_token=TokenInfo(symbol="USDC", address="", decimals=6, chain_id=8453),
        to_token=TokenInfo(symbol="WETH", address="", decimals=18, chain_id=8453),
        amount=Decimal("100"),
        chain_id=8453,
        wallet_address="0x55A5705453Ee82c742274154136Fce8149597058",
    )
    assert quote and quote.get("success"), f"Quote failed: {quote}"

    tx = await adapter.build_transaction(quote=quote, chain_id=8453)
    assert tx and not tx.get("error"), f"Tx build failed: {tx}"
    await adapter.close()


@pytest.mark.asyncio
async def test_smoke_quote_and_tx_build_eth_weth_usdc():
    adapter = UniswapAdapter()
    quote = await adapter.get_quote(
        from_token=TokenInfo(symbol="WETH", address="", decimals=18, chain_id=1),
        to_token=TokenInfo(symbol="USDC", address="", decimals=6, chain_id=1),
        amount=Decimal("0.1"),
        chain_id=1,
        wallet_address="0x55A5705453Ee82c742274154136Fce8149597058",
    )
    assert quote and quote.get("success"), f"Quote failed: {quote}"

    tx = await adapter.build_transaction(quote=quote, chain_id=1)
    assert tx and not tx.get("error"), f"Tx build failed: {tx}"
    await adapter.close()


@pytest.mark.asyncio
async def test_smoke_quote_and_tx_build_arbitrum_usdc_weth():
    adapter = UniswapAdapter()
    quote = await adapter.get_quote(
        from_token=TokenInfo(symbol="USDC", address="", decimals=6, chain_id=42161),
        to_token=TokenInfo(symbol="WETH", address="", decimals=18, chain_id=42161),
        amount=Decimal("50"),
        chain_id=42161,
        wallet_address="0x55A5705453Ee82c742274154136Fce8149597058",
    )
    assert quote and quote.get("success"), f"Quote failed: {quote}"

    tx = await adapter.build_transaction(quote=quote, chain_id=42161)
    assert tx and not tx.get("error"), f"Tx build failed: {tx}"
    await adapter.close()


# TODO: Add 25+ detailed tests for tiers, simulation, permit2, and error paths.