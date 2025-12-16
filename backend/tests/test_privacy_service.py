"""
Comprehensive test suite for privacy service and chain capabilities.
Tests all privacy routing scenarios across different chains.
"""
import pytest
from unittest.mock import MagicMock, patch
from backend.app.services.privacy_service import PrivacyService, PrivacyRoutingError
from backend.app.models.unified_models import PrivacyLevel, ChainPrivacyRoute
from backend.app.config.chains import PrivacyCapabilities


@pytest.fixture
def mock_config():
    """Mock config manager for testing."""
    return MagicMock()


@pytest.fixture
def privacy_service(mock_config):
    """Privacy service instance for testing."""
    return PrivacyService(mock_config)


class TestChainCapabilities:
    """Test chain privacy capabilities."""
    
    def test_ethereum_capabilities(self):
        """Test Ethereum privacy capabilities."""
        from backend.app.config.chains import get_privacy_capabilities, CHAINS
        
        eth_capabilities = get_privacy_capabilities(1)  # Ethereum
        assert eth_capabilities.x402_support == True
        assert eth_capabilities.gmp_privacy == True
        assert eth_capabilities.compliance_support == True
        assert eth_capabilities.direct_zcash == False
    
    def test_base_capabilities(self):
        """Test Base privacy capabilities."""
        from backend.app.config.chains import get_privacy_capabilities
        
        base_capabilities = get_privacy_capabilities(8453)  # Base
        assert base_capabilities.x402_support == True
        assert base_capabilities.gmp_privacy == True
        assert base_capabilities.compliance_support == True
    
    def test_scroll_capabilities(self):
        """Test Scroll privacy capabilities (GMP fallback only)."""
        from backend.app.config.chains import get_privacy_capabilities
        
        scroll_capabilities = get_privacy_capabilities(534352)  # Scroll
        assert scroll_capabilities.x402_support == False
        assert scroll_capabilities.gmp_privacy == True
        assert scroll_capabilities.compliance_support == False
    
    def test_zcash_capabilities(self):
        """Test Zcash privacy capabilities (direct only)."""
        from backend.app.config.chains import get_privacy_capabilities
        
        zcash_capabilities = get_privacy_capabilities(1337)  # Zcash
        assert zcash_capabilities.x402_support == False
        assert zcash_capabilities.gmp_privacy == False
        assert zcash_capabilities.compliance_support == True
        assert zcash_capabilities.direct_zcash == True


class TestPrivacyRouting:
    """Test privacy routing logic."""
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_x402_privacy_routing(self, mock_get_capabilities, privacy_service):
        """Test x402 privacy routing on supported chain."""
        # Mock Ethereum capabilities (x402 supported)
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=True,
            gmp_privacy=True,
            compliance_support=True
        )
        
        route = privacy_service.get_optimal_privacy_route(
            source_chain_id=1,  # Ethereum
            destination="zcash:u1test",
            privacy_level=PrivacyLevel.PRIVATE
        )
        
        assert route["method"] == "direct_zcash"
        assert route["privacy_level"] == PrivacyLevel.PRIVATE
        assert route["capabilities"]["compliance"] == True
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_gmp_fallback_routing(self, mock_get_capabilities, privacy_service):
        """Test GMP fallback routing when x402 unavailable."""
        # Mock Scroll capabilities (x402 not supported)
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=False,
            gmp_privacy=True,
            compliance_support=False
        )
        
        route = privacy_service.get_optimal_privacy_route(
            source_chain_id=534352,  # Scroll
            destination="zcash:u1test",
            privacy_level=PrivacyLevel.PRIVATE
        )
        
        assert route["method"] == "gmp_privacy"
        assert route["privacy_level"] == PrivacyLevel.PRIVATE
        assert route["capabilities"]["fallback"] == True
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_cross_chain_x402_routing(self, mock_get_capabilities, privacy_service):
        """Test x402 routing for cross-chain privacy transactions."""
        # Mock Ethereum capabilities
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=True,
            gmp_privacy=True,
            compliance_support=True
        )
        
        route = privacy_service.get_optimal_privacy_route(
            source_chain_id=1,  # Ethereum
            destination="0x123...",  # Non-Zcash address
            privacy_level=PrivacyLevel.PRIVATE
        )
        
        assert route["method"] == "x402_privacy"
        assert route["estimated_latency"] == "1-2min"
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_no_privacy_available(self, mock_get_capabilities, privacy_service):
        """Test error when no privacy available."""
        # Mock chain with no privacy support
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=False,
            gmp_privacy=False,
            compliance_support=False
        )
        
        with pytest.raises(PrivacyRoutingError) as exc_info:
            privacy_service.get_optimal_privacy_route(
                source_chain_id=999,  # Non-existent chain
                destination="0x123...",
                privacy_level=PrivacyLevel.PRIVATE
            )
        
        assert "No privacy route available" in str(exc_info.value)


class TestPrivacyValidation:
    """Test privacy request validation."""
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_validate_public_always_valid(self, mock_get_capabilities, privacy_service):
        """Test that public transactions are always valid."""
        # Should work even on chains with no privacy support
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=False,
            gmp_privacy=False
        )
        
        is_valid = privacy_service.validate_privacy_request(
            chain_id=999,
            privacy_level=PrivacyLevel.PUBLIC
        )
        assert is_valid == True
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_validate_private_with_x402(self, mock_get_capabilities, privacy_service):
        """Test private validation on x402-supported chain."""
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=True,
            gmp_privacy=True
        )
        
        is_valid = privacy_service.validate_privacy_request(
            chain_id=1,
            privacy_level=PrivacyLevel.PRIVATE
        )
        assert is_valid == True
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_validate_private_with_gmp_only(self, mock_get_capabilities, privacy_service):
        """Test private validation on GMP-only chain."""
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=False,
            gmp_privacy=True
        )
        
        is_valid = privacy_service.validate_privacy_request(
            chain_id=534352,  # Scroll
            privacy_level=PrivacyLevel.PRIVATE
        )
        assert is_valid == True
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_validate_compliance_requires_support(self, mock_get_capabilities, privacy_service):
        """Test compliance validation requires compliance support."""
        # Chain without compliance support
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=True,
            gmp_privacy=True,
            compliance_support=False
        )
        
        is_valid = privacy_service.validate_privacy_request(
            chain_id=1,
            privacy_level=PrivacyLevel.COMPLIANCE
        )
        assert is_valid == False
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_validate_compliance_with_support(self, mock_get_capabilities, privacy_service):
        """Test compliance validation with proper support."""
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=True,
            gmp_privacy=True,
            compliance_support=True
        )
        
        is_valid = privacy_service.validate_privacy_request(
            chain_id=1,
            privacy_level=PrivacyLevel.COMPLIANCE
        )
        assert is_valid == True


class TestChainPrivacyOptions:
    """Test chain-specific privacy options."""
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_ethereum_privacy_options(self, mock_get_capabilities, privacy_service):
        """Test Ethereum privacy options (full support)."""
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=True,
            gmp_privacy=True,
            compliance_support=True
        )
        
        options = privacy_service.get_chain_privacy_options(chain_id=1)
        
        assert len(options) == 3  # public, private, compliance
        assert any(opt["value"] == "public" for opt in options)
        assert any(opt["value"] == "private" for opt in options)
        assert any(opt["value"] == "compliance" for opt in options)
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_scroll_privacy_options(self, mock_get_capabilities, privacy_service):
        """Test Scroll privacy options (GMP only)."""
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=False,
            gmp_privacy=True,
            compliance_support=False
        )
        
        options = privacy_service.get_chain_privacy_options(chain_id=534352)
        
        assert len(options) == 2  # public, private (GMP)
        assert any(opt["value"] == "public" for opt in options)
        assert any(opt["value"] == "private" for opt in options)
        assert not any(opt["value"] == "compliance" for opt in options)
    
    @patch('backend.app.config.chains.get_privacy_capabilities')
    def test_no_privacy_options(self, mock_get_capabilities, privacy_service):
        """Test chain with no privacy options."""
        mock_get_capabilities.return_value = PrivacyCapabilities(
            x402_support=False,
            gmp_privacy=False
        )
        
        options = privacy_service.get_chain_privacy_options(chain_id=999)
        
        assert len(options) == 1  # public only
        assert options[0]["value"] == "public"


class TestCommandParserIntegration:
    """Test privacy command parsing integration."""
    
    def test_set_privacy_default_patterns(self):
        """Test SET_PRIVACY_DEFAULT command patterns."""
        from backend.app.core.parser.unified_parser import UnifiedParser
        
        parser = UnifiedParser()
        patterns = parser.get_supported_patterns(
            parser._get_command_type("set my default privacy to private")
        )
        
        assert any("Set default privacy level" in pattern for pattern in patterns)
    
    def test_override_privacy_patterns(self):
        """Test OVERRIDE_PRIVACY command patterns."""
        from backend.app.core.parser.unified_parser import UnifiedParser
        
        parser = UnifiedParser()
        patterns = parser.get_supported_patterns(
            parser._get_command_type("send this transaction privately")
        )
        
        assert any("Override privacy" in pattern for pattern in patterns)
    
    def test_x402_privacy_patterns(self):
        """Test X402_PRIVACY command patterns."""
        from backend.app.core.parser.unified_parser import UnifiedParser
        
        parser = UnifiedParser()
        patterns = parser.get_supported_patterns(
            parser._get_command_type("send via x402 privacy")
        )
        
        assert any("Explicit x402 privacy" in pattern for pattern in patterns)
    
    def test_bridge_to_privacy_patterns(self):
        """Test BRIDGE_TO_PRIVACY command patterns."""
        from backend.app.core.parser.unified_parser import UnifiedParser
        
        parser = UnifiedParser()
        patterns = parser.get_supported_patterns(
            parser._get_command_type("bridge 1 eth to zcash")
        )
        
        assert any("Bridge to Zcash" in pattern for pattern in patterns)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])