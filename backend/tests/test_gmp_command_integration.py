"""
Integration tests for GMP command processing.
Tests the complete flow from command parsing to GMP handler execution.
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from app.services.command_processor import CommandProcessor
from app.models.unified_models import UnifiedCommand, CommandType
from app.services.unified_command_parser import UnifiedCommandParser
from app.config.settings import Settings


class TestGMPCommandIntegration:
    """Test complete GMP command processing integration."""
    
    @pytest.fixture
    def mock_brian_client(self):
        """Mock Brian client for testing."""
        client = Mock()
        client.get_transfer_transaction = AsyncMock()
        client.get_swap_transaction = AsyncMock()
        return client
    
    @pytest.fixture
    def settings(self):
        """Mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.chains = Mock()
        settings.chains.supported_chains = {
            1: "Ethereum",
            137: "Polygon", 
            42161: "Arbitrum",
            8453: "Base"
        }
        return settings
    
    @pytest.fixture
    def command_processor(self, mock_brian_client, settings):
        """Create command processor with mocked dependencies."""
        return CommandProcessor(mock_brian_client, settings)

    def test_cross_chain_swap_command_detection(self):
        """Test that cross-chain swap commands are properly detected."""
        test_commands = [
            "swap 100 USDC from Ethereum to MATIC on Polygon",
            "swap 50 ETH from Ethereum for USDC on Arbitrum", 
            "cross-chain swap 200 USDC to DAI",
            "bridge and swap 100 USDC to MATIC"
        ]
        
        for command in test_commands:
            command_type = UnifiedCommandParser.detect_command_type(command)
            assert command_type == CommandType.CROSS_CHAIN_SWAP, f"Failed to detect cross-chain swap in: {command}"

    def test_gmp_operation_command_detection(self):
        """Test that GMP operation commands are properly detected."""
        test_commands = [
            "call mint function on Polygon",
            "execute mint() on Polygon contract 0x123...",
            "trigger stake function on Arbitrum",
            "add liquidity to Uniswap on Arbitrum using ETH from Ethereum",
            "stake tokens in Aave on Polygon using funds from Ethereum"
        ]
        
        for command in test_commands:
            command_type = UnifiedCommandParser.detect_command_type(command)
            assert command_type == CommandType.GMP_OPERATION, f"Failed to detect GMP operation in: {command}"

    def test_regular_swap_still_works(self):
        """Test that regular same-chain swaps still work correctly."""
        test_commands = [
            "swap 1 ETH for USDC",
            "swap 100 USDC to DAI",
            "swap $500 worth of ETH for USDC"
        ]
        
        for command in test_commands:
            command_type = UnifiedCommandParser.detect_command_type(command)
            assert command_type == CommandType.SWAP, f"Failed to detect regular swap in: {command}"

    @pytest.mark.asyncio
    async def test_ai_classification_includes_gmp(self, command_processor):
        """Test that AI classification includes GMP command types."""
        # Create a command that should be classified as cross-chain swap
        command = UnifiedCommand(
            command="swap 100 USDC from Ethereum to MATIC on Polygon",
            command_type=CommandType.UNKNOWN,
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            openai_api_key="test-key"
        )
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            # Mock AI response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "CROSS_CHAIN_SWAP"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Mock chat history service
            with patch('app.services.command_processor.chat_history_service') as mock_chat:
                mock_chat.get_recent_context.return_value = "No recent context"
                
                result = await command_processor._classify_with_ai(command)
                assert result == CommandType.CROSS_CHAIN_SWAP

    @pytest.mark.asyncio
    async def test_gmp_handler_integration(self, command_processor):
        """Test that GMP handler is properly integrated."""
        # Create a cross-chain swap command
        command = UnifiedCommand(
            command="swap 100 USDC from Ethereum to MATIC on Polygon",
            command_type=CommandType.CROSS_CHAIN_SWAP,
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            chain_id=1
        )
        
        # Mock the GMP handler
        with patch.object(command_processor, 'gmp_handler') as mock_handler:
            mock_handler.can_handle = AsyncMock(return_value=True)
            mock_handler.handle_cross_chain_swap = AsyncMock(return_value=Mock(
                success=True,
                message="Cross-chain swap prepared",
                content=Mock(
                    metadata={"uses_gmp": True, "axelar_powered": True}
                )
            ))
            
            # Test that the command processor routes to GMP handler
            should_use_gmp = await command_processor._should_use_gmp_handler(command)
            assert should_use_gmp is True
            
            # Test processing the command
            result = await command_processor._process_gmp_operation(command)
            assert result.success is True
            mock_handler.handle_cross_chain_swap.assert_called_once()

    @pytest.mark.asyncio
    async def test_cross_chain_swap_detection(self, command_processor):
        """Test cross-chain swap detection logic."""
        # Test explicit cross-chain command
        cross_chain_command = UnifiedCommand(
            command="swap 100 USDC from Ethereum to MATIC on Polygon",
            command_type=CommandType.CROSS_CHAIN_SWAP,
            from_chain="Ethereum",
            to_chain="Polygon"
        )
        
        is_cross_chain = await command_processor._is_cross_chain_swap(cross_chain_command)
        assert is_cross_chain is True
        
        # Test regular swap command
        regular_command = UnifiedCommand(
            command="swap 1 ETH for USDC",
            command_type=CommandType.SWAP
        )
        
        is_cross_chain = await command_processor._is_cross_chain_swap(regular_command)
        assert is_cross_chain is False

    @pytest.mark.asyncio
    async def test_end_to_end_gmp_processing(self, command_processor):
        """Test complete end-to-end GMP command processing."""
        # Create a cross-chain swap command
        command_text = "swap 100 USDC from Ethereum to MATIC on Polygon"
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Create unified command
        unified_command = CommandProcessor.create_unified_command(
            command=command_text,
            wallet_address=wallet_address,
            chain_id=1
        )
        
        # Mock all external dependencies
        with patch.object(command_processor, 'gmp_handler') as mock_gmp_handler, \
             patch.object(command_processor, 'gmp_service') as mock_gmp_service:
            
            # Mock GMP handler responses
            mock_gmp_handler.can_handle = AsyncMock(return_value=True)
            mock_gmp_handler.handle_cross_chain_swap = AsyncMock(return_value=Mock(
                success=True,
                message="Cross-chain swap prepared: 100 USDC on Ethereum → MATIC on Polygon",
                content=Mock(
                    transaction_data={
                        "type": "cross_chain_swap_gmp",
                        "protocol": "axelar_gmp",
                        "steps": [
                            {"type": "approve", "description": "Approve tokens"},
                            {"type": "pay_gas", "description": "Pay cross-chain gas"},
                            {"type": "call_contract", "description": "Execute swap"}
                        ]
                    },
                    metadata={
                        "uses_gmp": True,
                        "axelar_powered": True,
                        "source_chain": "Ethereum",
                        "dest_chain": "Polygon"
                    }
                )
            ))
            
            # Process the command
            result = await command_processor.process_command(unified_command)
            
            # Verify the result
            assert result.success is True
            assert "Cross-chain swap prepared" in result.message
            assert result.content.metadata["uses_gmp"] is True
            assert result.content.metadata["axelar_powered"] is True
            
            # Verify GMP handler was called
            mock_gmp_handler.can_handle.assert_called_once()
            mock_gmp_handler.handle_cross_chain_swap.assert_called_once()

    @pytest.mark.asyncio
    async def test_gmp_error_handling(self, command_processor):
        """Test error handling in GMP operations."""
        command = UnifiedCommand(
            command="swap 100 USDC from InvalidChain to MATIC on AnotherInvalidChain",
            command_type=CommandType.CROSS_CHAIN_SWAP,
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            chain_id=1
        )
        
        # Mock GMP handler to return error
        with patch.object(command_processor, 'gmp_handler') as mock_handler:
            mock_handler.can_handle = AsyncMock(return_value=True)
            mock_handler.handle_cross_chain_swap = AsyncMock(return_value=Mock(
                success=False,
                message="Invalid chain names provided",
                content=Mock(
                    error="Could not resolve chains: InvalidChain -> AnotherInvalidChain"
                )
            ))
            
            result = await command_processor._process_gmp_operation(command)
            assert result.success is False
            assert "Invalid chain names provided" in result.message

    def test_command_parser_patterns(self):
        """Test that command parser patterns work correctly."""
        parser = UnifiedCommandParser()
        
        # Test cross-chain swap patterns
        cross_chain_commands = [
            ("swap 100 USDC from Ethereum to MATIC on Polygon", CommandType.CROSS_CHAIN_SWAP),
            ("cross-chain swap 50 ETH to USDC", CommandType.CROSS_CHAIN_SWAP),
            ("bridge and swap 200 DAI to USDC", CommandType.CROSS_CHAIN_SWAP),
        ]
        
        for command, expected_type in cross_chain_commands:
            detected_type = parser.detect_command_type(command)
            assert detected_type == expected_type, f"Failed for command: {command}"
        
        # Test GMP operation patterns
        gmp_commands = [
            ("call mint function on Polygon", CommandType.GMP_OPERATION),
            ("execute stake() on Arbitrum", CommandType.GMP_OPERATION),
            ("add liquidity to Uniswap on Arbitrum using ETH from Ethereum", CommandType.GMP_OPERATION),
        ]
        
        for command, expected_type in gmp_commands:
            detected_type = parser.detect_command_type(command)
            assert detected_type == expected_type, f"Failed for command: {command}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
