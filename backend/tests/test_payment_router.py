"""
Tests for Unified Payment Router
Validates routing logic, protocol selection, and error handling
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from app.services.payment_router import PaymentRouter, PaymentPreparationResult
from app.protocols.x402_adapter import X402Adapter
from app.protocols.mnee_adapter import MNEEAdapter


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    os.environ['ETH_RPC_URL'] = 'https://eth-mainnet.g.alchemy.com/v2/test-key'
    os.environ['MNEE_RELAYER_ADDRESS'] = '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e'
    os.environ['MNEE_RELAYER_PRIVATE_KEY'] = '0x' + '1' * 64  # Test private key
    yield
    # Clean up
    for key in ['ETH_RPC_URL', 'MNEE_RELAYER_ADDRESS', 'MNEE_RELAYER_PRIVATE_KEY']:
        os.environ.pop(key, None)


class TestProtocolRouting:
    """Test protocol routing logic"""

    def setup_method(self):
        self.router = PaymentRouter()

    @pytest.mark.asyncio
    async def test_cronos_mainnet_usdc_routes_to_x402(self):
        """Test Cronos Mainnet + USDC routes to X402"""
        with patch.object(X402Adapter, 'create_unsigned_payment_payload') as mock_create:
            mock_create.return_value = {
                'domain': {},
                'types': {},
                'primaryType': 'TransferWithAuthorization',
                'message': {},
                'metadata': {'network': 'cronos-mainnet', 'scheme': 'exact', 'asset': 'USDC'}
            }
            
            result = await self.router.prepare_payment(
                network='cronos-mainnet',
                user_address='0x123',
                recipient_address='0x456',
                amount=100.0,
                token_symbol='USDC'
            )
            
            assert result.protocol == 'x402'
            assert result.action_type == 'sign_typed_data'

    @pytest.mark.asyncio
    async def test_cronos_testnet_usdc_routes_to_x402(self):
        """Test Cronos Testnet + USDC routes to X402"""
        with patch.object(X402Adapter, 'create_unsigned_payment_payload') as mock_create:
            mock_create.return_value = {
                'domain': {},
                'types': {},
                'primaryType': 'TransferWithAuthorization',
                'message': {},
                'metadata': {'network': 'cronos-testnet', 'scheme': 'exact', 'asset': 'USDC'}
            }
            
            result = await self.router.prepare_payment(
                network='cronos-testnet',
                user_address='0x123',
                recipient_address='0x456',
                amount=50.0,
                token_symbol='USDC'
            )
            
            assert result.protocol == 'x402'
            assert result.action_type == 'sign_typed_data'

    @pytest.mark.asyncio
    async def test_ethereum_mainnet_mnee_routes_to_relayer(self):
        """Test Ethereum Mainnet + MNEE routes to MNEE Relayer"""
        with patch.object(MNEEAdapter, 'get_relayer_address') as mock_relayer, \
             patch.object(MNEEAdapter, 'check_allowance') as mock_allowance:
            mock_relayer.return_value = '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e'
            mock_allowance.return_value = 1000000  # 10 MNEE (5 decimals)
            
            result = await self.router.prepare_payment(
                network='ethereum-mainnet',
                user_address='0x123',
                recipient_address='0x456',
                amount=5.0,
                token_symbol='MNEE'
            )
            
            assert result.protocol == 'mnee'
            assert result.action_type == 'ready_to_execute'
            assert result.allowance_sufficient == True

    @pytest.mark.asyncio
    async def test_ethereum_insufficient_allowance_requires_approval(self):
        """Test MNEE with insufficient allowance requires approval"""
        with patch.object(MNEEAdapter, 'get_relayer_address') as mock_relayer, \
             patch.object(MNEEAdapter, 'check_allowance') as mock_allowance:
            mock_relayer.return_value = '0x742d35Cc6634C0532925a3b8D4C9db96C4b5Da5e'
            mock_allowance.return_value = 100000  # 1 MNEE (5 decimals)
            
            result = await self.router.prepare_payment(
                network='ethereum-mainnet',
                user_address='0x123',
                recipient_address='0x456',
                amount=5.0,  # Need 5 MNEE but only have 1 approved
                token_symbol='MNEE'
            )
            
            assert result.protocol == 'mnee'
            assert result.action_type == 'approve_allowance'
            assert result.allowance_sufficient == False

    @pytest.mark.asyncio
    async def test_unsupported_network_raises_error(self):
        """Test unsupported network raises ValueError"""
        with pytest.raises(ValueError, match="No payment protocol found"):
            await self.router.prepare_payment(
                network='polygon-mainnet',
                user_address='0x123',
                recipient_address='0x456',
                amount=100.0,
                token_symbol='USDC'
            )

    @pytest.mark.asyncio
    async def test_unsupported_token_raises_error(self):
        """Test unsupported token on supported network raises error"""
        with pytest.raises(ValueError, match="Token ETH not supported on cronos-mainnet"):
            await self.router.prepare_payment(
                network='cronos-mainnet',
                user_address='0x123',
                recipient_address='0x456',
                amount=100.0,
                token_symbol='ETH'  # ETH not supported on Cronos
            )


class TestPaymentSubmission:
    """Test payment submission logic"""

    def setup_method(self):
        self.router = PaymentRouter()

    @pytest.mark.asyncio
    async def test_x402_submission_success(self):
        """Test successful X402 payment submission"""
        mock_result = Mock()
        mock_result.success = True
        mock_result.txHash = '0xabc123'
        mock_result.network = 'cronos-testnet'
        mock_result.blockNumber = 12345
        mock_result.timestamp = '2024-01-01T00:00:00Z'
        mock_result.error = None
        mock_result.from_address = '0x123'
        mock_result.to_address = '0x456'
        mock_result.value = '100000000'
        
        with patch.object(X402Adapter, 'construct_payment_header_from_signature') as mock_construct, \
             patch.object(X402Adapter, 'settle_payment') as mock_settle:
            mock_construct.return_value = 'base64_header'
            mock_settle.return_value = mock_result
            
            result = await self.router.submit_payment('x402', {
                'signature': '0xsignature',
                'user_address': '0x123',
                'message': {'to': '0x456', 'value': 100000000},
                'metadata': {
                    'network': 'cronos-testnet',
                    'scheme': 'exact',
                    'asset': 'USDC'
                }
            })
            
            assert result['success'] == True
            assert result['txHash'] == '0xabc123'

    @pytest.mark.asyncio
    async def test_mnee_submission_success(self):
        """Test successful MNEE payment submission"""
        with patch.object(MNEEAdapter, 'execute_relayed_transfer') as mock_transfer:
            mock_transfer.return_value = '0xdef456'
            
            result = await self.router.submit_payment('mnee', {
                'metadata': {
                    'user_address': '0x123',
                    'recipient_address': '0x456',
                    'amount': 10.0
                }
            })
            
            assert result['success'] == True
            assert result['txHash'] == '0xdef456'
            assert result['protocol'] == 'mnee'

    @pytest.mark.asyncio
    async def test_unknown_protocol_raises_error(self):
        """Test unknown protocol raises ValueError"""
        with pytest.raises(ValueError, match="Unknown protocol: unknown"):
            await self.router.submit_payment('unknown', {})


class TestProtocolFeatures:
    """Test protocol feature detection"""

    def setup_method(self):
        self.router = PaymentRouter()

    def test_x402_features(self):
        """Test X402 protocol features"""
        # This would test feature detection if implemented
        # For now, just verify the router exists
        assert self.router is not None

    def test_mnee_features(self):
        """Test MNEE protocol features"""
        # This would test feature detection if implemented
        # For now, just verify the router exists
        assert self.router is not None