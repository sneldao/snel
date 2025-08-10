"""
Integration tests for Axelar GMP functionality.
Tests the complete flow from command parsing to transaction building.
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from app.services.axelar_gmp_service import (
    AxelarGMPService, 
    CrossChainSwapParams, 
    GMPCallData,
    axelar_gmp_service
)
from app.services.enhanced_crosschain_handler import enhanced_crosschain_handler
from app.models.unified_models import UnifiedCommand, CommandType


class TestAxelarGMPService:
    """Test cases for Axelar GMP Service."""
    
    @pytest.fixture
    def gmp_service(self):
        """Create GMP service instance for testing."""
        return AxelarGMPService()
    
    @pytest.fixture
    def sample_swap_params(self):
        """Sample cross-chain swap parameters."""
        return CrossChainSwapParams(
            source_chain="Ethereum",
            dest_chain="Polygon",
            source_token="USDC",
            dest_token="USDC",
            amount=Decimal("100.0"),
            recipient="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            slippage=0.01
        )
    
    @pytest.fixture
    def sample_gmp_call(self):
        """Sample GMP call data."""
        return GMPCallData(
            destination_chain="Polygon",
            destination_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            payload="0x1234567890abcdef",
            gas_limit=500000,
            gas_token="ETH"
        )

    def test_gateway_address_retrieval(self, gmp_service):
        """Test gateway address retrieval for supported chains."""
        # Test Ethereum
        eth_gateway = gmp_service.get_gateway_address(1)
        assert eth_gateway == "0x4F4495243837681061C4743b74B3eEdf548D56A5"
        
        # Test Polygon
        polygon_gateway = gmp_service.get_gateway_address(137)
        assert polygon_gateway == "0x6f015F16De9fC8791b234eF68D486d2bF203FBA8"
        
        # Test unsupported chain
        unsupported = gmp_service.get_gateway_address(999999)
        assert unsupported is None

    def test_gas_service_address_retrieval(self, gmp_service):
        """Test gas service address retrieval for supported chains."""
        # Test Ethereum
        eth_gas_service = gmp_service.get_gas_service_address(1)
        assert eth_gas_service == "0x2d5d7d31F671F86C782533cc367F14109a082712"
        
        # Test unsupported chain
        unsupported = gmp_service.get_gas_service_address(999999)
        assert unsupported is None

    @pytest.mark.asyncio
    async def test_estimate_gas_fee_success(self, gmp_service):
        """Test successful gas fee estimation."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "gasPrice": "0.05",
                "estimatedCostUSD": "2.50"
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await gmp_service.estimate_gas_fee(1, 137, 500000, "ETH")
            
            assert result["success"] is True
            assert result["gas_fee"] == "0.05"
            assert result["estimated_cost_usd"] == "2.50"

    @pytest.mark.asyncio
    async def test_estimate_gas_fee_unsupported_chain(self, gmp_service):
        """Test gas fee estimation with unsupported chain."""
        result = await gmp_service.estimate_gas_fee(999999, 137, 500000, "ETH")
        
        assert "error" in result
        assert "Unsupported chain" in result["error"]

    @pytest.mark.asyncio
    async def test_build_cross_chain_swap_transaction(self, gmp_service, sample_swap_params):
        """Test building cross-chain swap transaction."""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        with patch.object(gmp_service, 'estimate_gas_fee') as mock_estimate:
            mock_estimate.return_value = {
                "success": True,
                "gas_fee": "0.05",
                "estimated_cost_usd": "2.50"
            }
            
            result = await gmp_service.build_cross_chain_swap_transaction(
                sample_swap_params, wallet_address
            )
            
            assert result["success"] is True
            assert result["protocol"] == "axelar_gmp"
            assert result["type"] == "cross_chain_swap"
            assert result["source_chain"] == "Ethereum"
            assert result["dest_chain"] == "Polygon"
            assert len(result["steps"]) == 3  # approve, pay_gas, call_contract

    @pytest.mark.asyncio
    async def test_build_gmp_call(self, gmp_service, sample_gmp_call):
        """Test building GMP call transaction."""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        with patch.object(gmp_service, 'estimate_gas_fee') as mock_estimate:
            mock_estimate.return_value = {
                "success": True,
                "gas_fee": "0.02",
                "estimated_cost_usd": "1.00"
            }
            
            result = await gmp_service.build_gmp_call(
                sample_gmp_call, 1, wallet_address
            )
            
            assert result["success"] is True
            assert result["protocol"] == "axelar_gmp"
            assert result["type"] == "general_message_passing"
            assert result["destination_chain"] == "Polygon"

    @pytest.mark.asyncio
    async def test_track_gmp_transaction(self, gmp_service):
        """Test GMP transaction tracking."""
        tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful tracking response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "executed",
                "destinationTxHash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "gasPaid": True,
                "approved": True,
                "executed": True
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await gmp_service.track_gmp_transaction(tx_hash, 1, 137)
            
            assert result["success"] is True
            assert result["status"] == "executed"
            assert result["gas_paid"] is True
            assert result["approved"] is True
            assert result["executed"] is True


class TestEnhancedCrossChainHandler:
    """Test cases for Enhanced Cross-Chain Handler."""
    
    @pytest.fixture
    def handler(self):
        """Create handler instance for testing."""
        return enhanced_crosschain_handler
    
    @pytest.fixture
    def sample_cross_chain_command(self):
        """Sample cross-chain command."""
        return UnifiedCommand(
            command_type=CommandType.SWAP,
            original_text="swap 100 USDC from Ethereum to MATIC on Polygon",
            from_token="USDC",
            to_token="MATIC",
            amount=Decimal("100.0"),
            from_chain="Ethereum",
            to_chain="Polygon",
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )

    @pytest.mark.asyncio
    async def test_can_handle_cross_chain_swap(self, handler, sample_cross_chain_command):
        """Test handler can identify cross-chain swap commands."""
        can_handle = await handler.can_handle(sample_cross_chain_command)
        assert can_handle is True

    @pytest.mark.asyncio
    async def test_can_handle_gmp_operation(self, handler):
        """Test handler can identify GMP operations."""
        gmp_command = UnifiedCommand(
            command_type=CommandType.CUSTOM,
            original_text="execute mint function on Polygon chain",
            chain_id=1
        )
        
        can_handle = await handler.can_handle(gmp_command)
        assert can_handle is True

    @pytest.mark.asyncio
    async def test_handle_cross_chain_swap_success(self, handler, sample_cross_chain_command):
        """Test successful cross-chain swap handling."""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        with patch.object(handler.gmp_service, 'build_cross_chain_swap_transaction') as mock_build:
            mock_build.return_value = {
                "success": True,
                "steps": [{"type": "approve", "description": "Approve tokens"}],
                "estimated_gas_fee": "0.05",
                "estimated_cost_usd": "2.50",
                "gateway_address": "0x123...",
                "gas_service_address": "0x456..."
            }
            
            result = await handler.handle_cross_chain_swap(
                sample_cross_chain_command, wallet_address
            )
            
            assert result.success is True
            assert "Cross-chain swap prepared" in result.message
            assert result.content.metadata["uses_gmp"] is True
            assert result.content.metadata["axelar_powered"] is True

    @pytest.mark.asyncio
    async def test_handle_cross_chain_swap_failure(self, handler, sample_cross_chain_command):
        """Test cross-chain swap handling with failure."""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        with patch.object(handler.gmp_service, 'build_cross_chain_swap_transaction') as mock_build:
            mock_build.return_value = {
                "success": False,
                "error": "Insufficient liquidity",
                "technical_details": "Not enough tokens in pool"
            }
            
            result = await handler.handle_cross_chain_swap(
                sample_cross_chain_command, wallet_address
            )
            
            assert result.success is False
            assert "Insufficient liquidity" in result.message

    @pytest.mark.asyncio
    async def test_get_supported_operations(self, handler):
        """Test getting supported operations."""
        operations = await handler.get_supported_operations()
        
        assert "cross_chain_swap" in operations
        assert "general_message_passing" in operations
        assert "cross_chain_contract_call" in operations

    @pytest.mark.asyncio
    async def test_get_supported_chains(self, handler):
        """Test getting supported chains."""
        chains = await handler.get_supported_chains()
        
        assert "Ethereum" in chains
        assert "Polygon" in chains
        assert "Arbitrum" in chains


class TestGMPIntegration:
    """Integration tests for complete GMP flow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_cross_chain_swap(self):
        """Test complete end-to-end cross-chain swap flow."""
        # Create command
        command = UnifiedCommand(
            command_type=CommandType.SWAP,
            original_text="swap 50 USDC from Ethereum to USDC on Polygon",
            from_token="USDC",
            to_token="USDC",
            amount=Decimal("50.0"),
            from_chain="Ethereum",
            to_chain="Polygon",
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
        
        # Mock external dependencies
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "gasPrice": "0.03",
                "estimatedCostUSD": "1.50"
            }
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            # Test handler can handle the command
            can_handle = await enhanced_crosschain_handler.can_handle(command)
            assert can_handle is True
            
            # Test handling the command
            result = await enhanced_crosschain_handler.handle_cross_chain_swap(
                command, command.wallet_address
            )
            
            assert result.success is True
            assert result.content.transaction_data["type"] == "cross_chain_swap_gmp"
            assert result.content.metadata["uses_gmp"] is True

    @pytest.mark.asyncio
    async def test_error_handling_invalid_chain(self):
        """Test error handling for invalid chains."""
        command = UnifiedCommand(
            command_type=CommandType.SWAP,
            original_text="swap 50 USDC from InvalidChain to USDC on AnotherInvalidChain",
            from_token="USDC",
            to_token="USDC",
            amount=Decimal("50.0"),
            from_chain="InvalidChain",
            to_chain="AnotherInvalidChain",
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
        
        result = await enhanced_crosschain_handler.handle_cross_chain_swap(
            command, command.wallet_address
        )
        
        # Should handle gracefully and return error
        assert result.success is False
        assert "error" in result.content.error.lower() or "invalid" in result.message.lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
