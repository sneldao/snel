"""
Integration tests for X402 agentic payment protocol
Tests both Cronos and Ethereum network support
"""
import pytest
import asyncio
from app.protocols.x402_adapter import (
    X402Adapter,
    execute_ai_payment,
    check_x402_service_health,
    FACILITATOR_URLS,
    STABLECOIN_CONTRACTS,
    CHAIN_IDS,
    STABLECOIN_SYMBOLS
)
from app.models.unified_models import CommandType
from app.core.parser.unified_parser import unified_parser
from app.services.processors.x402_processor import X402Processor


class TestX402Configuration:
    """Test x402 configuration constants."""
    
    def test_supported_networks(self):
        """Test that all required networks are configured."""
        expected_networks = ["cronos-mainnet", "cronos-testnet", "ethereum-mainnet"]
        
        for network in expected_networks:
            assert network in FACILITATOR_URLS, f"{network} missing from FACILITATOR_URLS"
            assert network in STABLECOIN_CONTRACTS, f"{network} missing from STABLECOIN_CONTRACTS"
            assert network in CHAIN_IDS, f"{network} missing from CHAIN_IDS"
            assert network in STABLECOIN_SYMBOLS, f"{network} missing from STABLECOIN_SYMBOLS"
    
    def test_stablecoin_symbols(self):
        """Test correct stablecoin symbols for each network."""
        assert STABLECOIN_SYMBOLS["cronos-mainnet"] == "USDC"
        assert STABLECOIN_SYMBOLS["cronos-testnet"] == "USDC"
        assert STABLECOIN_SYMBOLS["ethereum-mainnet"] == "MNEE"
    
    def test_chain_ids(self):
        """Test correct chain IDs."""
        assert CHAIN_IDS["cronos-mainnet"] == 25
        assert CHAIN_IDS["cronos-testnet"] == 338
        assert CHAIN_IDS["ethereum-mainnet"] == 1


class TestX402Adapter:
    """Test X402Adapter initialization and methods."""
    
    def test_adapter_initialization_cronos(self):
        """Test adapter initializes correctly for Cronos."""
        adapter = X402Adapter("cronos-testnet")
        
        assert adapter.network == "cronos-testnet"
        assert adapter.chain_id == 338
        assert adapter.stablecoin_symbol == "USDC"
        assert adapter.network_name == "Cronos Testnet"
        assert adapter.stablecoin_contract == STABLECOIN_CONTRACTS["cronos-testnet"]
    
    def test_adapter_initialization_ethereum(self):
        """Test adapter initializes correctly for Ethereum."""
        adapter = X402Adapter("ethereum-mainnet")
        
        assert adapter.network == "ethereum-mainnet"
        assert adapter.chain_id == 1
        assert adapter.stablecoin_symbol == "MNEE"
        assert adapter.network_name == "Ethereum"
        assert adapter.stablecoin_contract == STABLECOIN_CONTRACTS["ethereum-mainnet"]
    
    def test_adapter_invalid_network(self):
        """Test adapter raises error for invalid network."""
        with pytest.raises(ValueError, match="Unsupported network"):
            X402Adapter("invalid-network")
    
    def test_backward_compatibility(self):
        """Test backward compatibility with usdc_contract attribute."""
        adapter = X402Adapter("cronos-testnet")
        assert adapter.usdc_contract == adapter.stablecoin_contract


class TestX402CommandParsing:
    """Test command parsing for x402 automation."""
    
    def test_parse_rebalancing_command(self):
        """Test parsing portfolio rebalancing command."""
        command = "setup monthly portfolio rebalancing with 50 USDC budget"
        cmd_type, details = unified_parser.parse_command(command)
        
        assert cmd_type == CommandType.X402_PAYMENT
    
    def test_parse_yield_farming_command(self):
        """Test parsing yield farming automation command."""
        command = "setup weekly 100 USDC for yield farming when APY > 15%"
        cmd_type, details = unified_parser.parse_command(command)
        
        assert cmd_type == CommandType.X402_PAYMENT
    
    def test_parse_automated_bridge_command(self):
        """Test parsing automated bridge command."""
        command = "create automated bridge 200 USDC monthly to polygon"
        cmd_type, details = unified_parser.parse_command(command)
        
        assert cmd_type == CommandType.X402_PAYMENT
    
    def test_parse_agent_payment_command(self):
        """Test parsing AI agent payment command."""
        command = "pay agent 10 USDC for API calls"
        cmd_type, details = unified_parser.parse_command(command)
        
        assert cmd_type == CommandType.X402_PAYMENT
    
    def test_parse_agentic_automation_command(self):
        """Test parsing general agentic automation command."""
        command = "ai payment automation"
        cmd_type, details = unified_parser.parse_command(command)
        
        assert cmd_type == CommandType.X402_PAYMENT


@pytest.mark.asyncio
class TestX402Processor:
    """Test X402 processor with different networks."""
    
    async def test_processor_cronos_network_suggestion(self):
        """Test processor suggests Cronos when on unsupported network."""
        processor = X402Processor()
        
        # Create command on Polygon (chain_id 137)
        unified_command = unified_parser.create_unified_command(
            command="setup portfolio rebalancing",
            chain_id=137,
            wallet_address="0x1234567890123456789012345678901234567890"
        )
        
        response = await processor.process(unified_command)
        
        assert "Cronos" in response.content
        assert response.metadata.get("command_type") == CommandType.X402_PAYMENT
    
    async def test_processor_on_cronos(self):
        """Test processor works on Cronos network."""
        processor = X402Processor()
        
        # Create command on Cronos testnet (chain_id 338)
        unified_command = unified_parser.create_unified_command(
            command="setup monthly portfolio rebalancing with 50 USDC",
            chain_id=338,
            wallet_address="0x1234567890123456789012345678901234567890"
        )
        
        response = await processor.process(unified_command)
        
        assert response.status == "success"
        assert "rebalancing" in response.content.lower()
    
    async def test_processor_on_ethereum(self):
        """Test processor works on Ethereum network."""
        processor = X402Processor()
        
        # Create command on Ethereum mainnet (chain_id 1)
        unified_command = unified_parser.create_unified_command(
            command="setup monthly portfolio rebalancing with 50 MNEE",
            chain_id=1,
            wallet_address="0x1234567890123456789012345678901234567890"
        )
        
        response = await processor.process(unified_command)
        
        assert response.status == "success"
        assert "rebalancing" in response.content.lower()


@pytest.mark.asyncio
class TestX402NetworkSupport:
    """Test x402 support across different networks."""
    
    async def test_network_detection(self):
        """Test that x402 is properly detected on supported networks."""
        from app.config.chains import is_x402_privacy_supported
        
        # Test Cronos support
        assert is_x402_privacy_supported(25) == True  # Cronos mainnet
        assert is_x402_privacy_supported(338) == True  # Cronos testnet
        
        # Test Ethereum support
        assert is_x402_privacy_supported(1) == True  # Ethereum mainnet
    
    async def test_cronos_protocols(self):
        """Test Cronos has x402 in supported protocols."""
        from app.config.chains import CHAINS
        
        cronos_mainnet = CHAINS[25]
        cronos_testnet = CHAINS[338]
        
        assert "x402" in cronos_mainnet.supported_protocols
        assert "x402" in cronos_testnet.supported_protocols
    
    async def test_ethereum_protocols(self):
        """Test Ethereum has x402 in supported protocols."""
        from app.config.chains import CHAINS
        
        ethereum = CHAINS[1]
        
        assert "x402" in ethereum.supported_protocols


class TestX402Documentation:
    """Test that x402 has proper documentation."""
    
    def test_adapter_docstrings(self):
        """Test adapter has proper docstrings."""
        assert X402Adapter.__doc__ is not None
        assert "Ethereum" in X402Adapter.__doc__
        assert "Cronos" in X402Adapter.__doc__
    
    def test_convenience_function_docstrings(self):
        """Test convenience functions have proper documentation."""
        assert execute_ai_payment.__doc__ is not None
        assert "Ethereum" in execute_ai_payment.__doc__ or "supported networks" in execute_ai_payment.__doc__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
