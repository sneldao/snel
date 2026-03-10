"""
Tests for Starknet service integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from app.services.starknet_service import StarknetService

@pytest.fixture
def starknet_service():
    with patch('app.services.starknet_service.FullNodeClient') as mock_client:
        service = StarknetService()
        # Mock client for SN_MAIN
        service.clients['SN_MAIN'] = mock_client.return_value
        return service

@pytest.mark.asyncio
async def test_get_native_balance(starknet_service):
    # Mock result for balanceOf (Uint256: low, high)
    # 1 ETH = 10^18 wei = 0xde0b6b3a7640000
    starknet_service.clients['SN_MAIN'].call_contract = AsyncMock(return_value=[0xde0b6b3a7640000, 0])
    
    balance = await starknet_service.get_native_balance("0x123", "SN_MAIN")
    assert balance == 1.0
    starknet_service.clients['SN_MAIN'].call_contract.assert_called_once()

@pytest.mark.asyncio
async def test_get_token_metadata(starknet_service):
    # Mock decimals and symbol
    # selector for decimals usually returns [18]
    # selector for symbol usually returns [felt_of_symbol]
    
    mock_call = AsyncMock()
    mock_call.side_effect = [
        [18], # decimals
        [int.from_bytes(b"USDC", "big")] # symbol
    ]
    starknet_service.clients['SN_MAIN'].call_contract = mock_call
    
    metadata = await starknet_service.get_token_metadata("0x456", "SN_MAIN")
    assert metadata["symbol"] == "USDC"
    assert metadata["decimals"] == 18

def test_build_shield_tx(starknet_service):
    tx = starknet_service.build_shield_tx(
        token_address="0xETH",
        amount=Decimal("1.5"),
        commitment="0xABC"
    )
    
    assert tx["entrypoint"] == "deposit"
    assert tx["calldata"][0] == "0xABC"
    assert tx["calldata"][1] == str(int(1.5 * 10**18))

def test_build_unshield_tx(starknet_service):
    tx = starknet_service.build_unshield_tx(
        nullifier="0xNULL",
        recipient="0xREC",
        amount=Decimal("1.0"),
        proof=["0xP1", "0xP2"]
    )
    
    assert tx["entrypoint"] == "withdraw"
    assert "0xNULL" in tx["calldata"]
    assert "0xREC" in tx["calldata"]
    assert "2" in tx["calldata"] # proof length
