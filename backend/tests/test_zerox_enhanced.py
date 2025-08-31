"""
Comprehensive tests for Enhanced 0x Protocol v2 with Permit2 support.

This test suite validates the enhanced 0x protocol implementation including:
- Permit2 EIP-712 signature handling
- Enhanced quote processing
- Circuit breaker functionality
- Rate limiting behavior
- Error handling scenarios
- Performance monitoring

Test Coverage:
- Unit tests for all core functionality
- Integration tests with mocked 0x API responses
- Error handling validation
- Performance and reliability testing
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

# Import modules under test
from app.protocols.zerox_enhanced import (
    ZeroXEnhanced, EnhancedSwapQuote, Permit2Data, AllowanceInfo,
    Permit2Handler, QuoteType
)
from app.core.errors import (
    ProtocolError, ValidationError, RateLimitError,
    InsufficientLiquidityError, ProtocolAPIError, NetworkError
)


# Test fixtures and constants
TEST_CHAINS = {
    1: "ethereum",
    8453: "base",
    42161: "arbitrum"
}

TEST_TOKENS = {
    "WETH": {
        1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        8453: "0x4200000000000000000000000000000000000006",
        42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
    },
    "USDC": {
        1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
        42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
    }
}

TEST_WALLET = "0x742d35Cc6634C0532925a3b8D72cd534e6c15E28"

# Mock API responses
MOCK_PRICE_RESPONSE = {
    "buyAmount": "1500000000",
    "sellAmount": "1000000000000000000",
    "buyToken": TEST_TOKENS["USDC"][1],
    "sellToken": TEST_TOKENS["WETH"][1],
    "gas": "180000",
    "gasPrice": "25000000000",
    "estimatedPriceImpact": 0.15,
    "issues": {
        "allowance": {
            "actual": "0",
            "spender": "0x000000000022d473030f116ddee9f6b43ac78ba3"
        }
    }
}

MOCK_QUOTE_RESPONSE = {
    "buyAmount": "1500000000",
    "sellAmount": "1000000000000000000",
    "buyToken": TEST_TOKENS["USDC"][1],
    "sellToken": TEST_TOKENS["WETH"][1],
    "gas": "180000",
    "gasPrice": "25000000000",
    "estimatedPriceImpact": 0.15,
    "transaction": {
        "to": "0x1234567890123456789012345678901234567890",
        "data": "0xabcdef123456",
        "value": "0"
    },
    "permit2": {
        "type": "Permit2",
        "hash": "0xdef456789012345678901234567890123456789012345678901234567890abcdef",
        "eip712": {
            "types": {
                "PermitTransferFrom": [
                    {"name": "permitted", "type": "TokenPermissions"},
                    {"name": "spender", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "TokenPermissions": [
                    {"name": "token", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ]
            },
            "domain": {
                "name": "Permit2",
                "chainId": 1,
                "verifyingContract": "0x000000000022d473030f116ddee9f6b43ac78ba3"
            },
            "message": {
                "permitted": {
                    "token": TEST_TOKENS["WETH"][1],
                    "amount": "1000000000000000000"
                },
                "spender": "0x1234567890123456789012345678901234567890",
                "nonce": "123456789",
                "deadline": "1703980800"
            },
            "primaryType": "PermitTransferFrom"
        }
    },
    "issues": {
        "allowance": {
            "actual": "0",
            "spender": "0x000000000022d473030f116ddee9f6b43ac78ba3"
        }
    },
    "route": {
        "fills": [
            {"source": "Uniswap_V3", "proportionBps": "7500"},
            {"source": "SushiSwap", "proportionBps": "2500"}
        ]
    }
}


class TestPermit2Handler:
    """Test suite for Permit2Handler utilities."""

    def test_validate_eip712_message_valid(self):
        """Test EIP-712 message validation with valid data."""
        handler = Permit2Handler()

        valid_message = MOCK_QUOTE_RESPONSE["permit2"]["eip712"]

        assert handler.validate_eip712_message(valid_message) == True

    def test_validate_eip712_message_invalid_domain(self):
        """Test EIP-712 validation with invalid domain."""
        handler = Permit2Handler()

        invalid_message = MOCK_QUOTE_RESPONSE["permit2"]["eip712"].copy()
        invalid_message["domain"]["name"] = "InvalidContract"

        assert handler.validate_eip712_message(invalid_message) == False

    def test_validate_eip712_message_missing_fields(self):
        """Test EIP-712 validation with missing required fields."""
        handler = Permit2Handler()

        incomplete_message = {"types": {}, "domain": {}}

        assert handler.validate_eip712_message(incomplete_message) == False

    def test_calculate_signature_length(self):
        """Test signature length calculation."""
        handler = Permit2Handler()

        # Test signature without 0x prefix
        signature = "1234567890abcdef" * 8  # 128 hex chars = 64 bytes
        expected_length = "0x0000000000000000000000000000000000000000000000000000000000000040"

        result = handler.calculate_signature_length(signature)
        assert result == expected_length

    def test_concat_transaction_data(self):
        """Test transaction data concatenation with signature."""
        handler = Permit2Handler()

        original_data = "0xabcdef123456"
        signature = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

        result = handler.concat_transaction_data(original_data, signature)

        # Should contain original data + signature length + signature
        assert result.startswith("0xabcdef123456")
        assert signature[2:] in result
        assert len(result) > len(original_data) + len(signature)


class TestEnhancedSwapQuote:
    """Test suite for EnhancedSwapQuote data model."""

    def test_quote_creation_from_api_response(self):
        """Test creating enhanced quote from API response data."""
        permit2_data = Permit2Data.from_api_response(MOCK_QUOTE_RESPONSE["permit2"])
        allowance_info = AllowanceInfo.from_api_response(MOCK_QUOTE_RESPONSE["issues"])

        quote = EnhancedSwapQuote(
            buy_amount="1500000000",
            sell_amount="1000000000000000000",
            buy_token=TEST_TOKENS["USDC"][1],
            sell_token=TEST_TOKENS["WETH"][1],
            price=1500.0,
            estimated_price_impact=0.15,
            gas_estimate=180000,
            gas_price="25000000000",
            transaction_to="0x1234567890123456789012345678901234567890",
            transaction_data="0xabcdef123456",
            transaction_value="0",
            permit2_data=permit2_data,
            allowance_info=allowance_info,
            expires_at=datetime.utcnow() + timedelta(seconds=30),
            chain_id=1,
            quote_type=QuoteType.FIRM,
            sources=[]
        )

        assert quote.requires_permit2_signature == True
        assert quote.requires_allowance == True
        assert quote.buy_amount == "1500000000"
        assert quote.chain_id == 1

    def test_permit2_data_from_api_response(self):
        """Test Permit2Data creation from API response."""
        permit2_dict = MOCK_QUOTE_RESPONSE["permit2"]

        permit2_data = Permit2Data.from_api_response(permit2_dict)

        assert permit2_data.permit_type == "Permit2"
        assert permit2_data.requires_signature == True
        assert permit2_data.deadline > 0
        assert "PermitTransferFrom" in permit2_data.eip712["types"]

    def test_allowance_info_from_api_response(self):
        """Test AllowanceInfo creation from API response."""
        issues_dict = MOCK_QUOTE_RESPONSE["issues"]

        allowance_info = AllowanceInfo.from_api_response(issues_dict)

        assert allowance_info is not None
        assert allowance_info.required == True
        assert allowance_info.spender == "0x000000000022d473030f116ddee9f6b43ac78ba3"
        assert allowance_info.current_allowance == "0"


class TestZeroXEnhanced:
    """Test suite for ZeroXEnhanced protocol implementation."""

    @pytest.fixture
    async def enhanced_zerox(self):
        """Create and initialize ZeroXEnhanced instance with mocked config."""
        protocol = ZeroXEnhanced()

        # Mock configuration manager
        with patch('app.protocols.zerox_enhanced.config_manager') as mock_config_manager:
            mock_config = AsyncMock()
            mock_config.api_keys = {"default": "test_api_key"}
            mock_config.supported_chains = {1, 8453, 42161}
            mock_config.api_endpoints = {
                "1": "https://api.0x.org",
                "8453": "https://base.api.0x.org",
                "42161": "https://arbitrum.api.0x.org"
            }
            mock_config_manager.get_protocol.return_value = mock_config

            await protocol.initialize()

        yield protocol
        await protocol.close()

    @pytest.mark.asyncio
    async def test_initialization_success(self):
        """Test successful protocol initialization."""
        protocol = ZeroXEnhanced()

        with patch('app.protocols.zerox_enhanced.config_manager') as mock_config_manager:
            mock_config = AsyncMock()
            mock_config.api_keys = {"default": "test_api_key"}
            mock_config.supported_chains = {1, 8453, 42161}
            mock_config.api_endpoints = {
                "1": "https://api.0x.org",
                "8453": "https://base.api.0x.org"
            }
            mock_config_manager.get_protocol.return_value = mock_config

            await protocol.initialize()

            assert protocol.session is not None
            assert protocol.config is not None
            assert protocol.is_supported(1) == True
            assert protocol.is_supported(999999) == False

        await protocol.close()

    @pytest.mark.asyncio
    async def test_initialization_no_config(self):
        """Test initialization failure when config is missing."""
        protocol = ZeroXEnhanced()

        with patch('app.protocols.zerox_enhanced.config_manager') as mock_config_manager:
            mock_config_manager.get_protocol.return_value = None

            with pytest.raises(ProtocolError) as exc_info:
                await protocol.initialize()

            assert "configuration not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialization_no_api_key(self):
        """Test initialization failure when API key is missing."""
        protocol = ZeroXEnhanced()

        with patch('app.protocols.zerox_enhanced.config_manager') as mock_config_manager:
            mock_config = AsyncMock()
            mock_config.api_keys = {}  # No API key
            mock_config_manager.get_protocol.return_value = mock_config

            with pytest.raises(ProtocolError) as exc_info:
                await protocol.initialize()

            assert "API key not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_indicative_price_success(self, enhanced_zerox):
        """Test successful indicative price retrieval."""
        protocol = enhanced_zerox

        with patch.object(protocol, '_make_api_request', return_value=MOCK_PRICE_RESPONSE):
            quote = await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1,
                taker_address=TEST_WALLET
            )

            assert isinstance(quote, EnhancedSwapQuote)
            assert quote.quote_type == QuoteType.INDICATIVE
            assert quote.buy_amount == "1500000000"
            assert quote.chain_id == 1
            assert quote.requires_allowance == True

    @pytest.mark.asyncio
    async def test_get_firm_quote_success(self, enhanced_zerox):
        """Test successful firm quote retrieval with permit2."""
        protocol = enhanced_zerox

        with patch.object(protocol, '_make_api_request', return_value=MOCK_QUOTE_RESPONSE):
            quote = await protocol.get_firm_quote(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1,
                taker_address=TEST_WALLET
            )

            assert isinstance(quote, EnhancedSwapQuote)
            assert quote.quote_type == QuoteType.FIRM
            assert quote.requires_permit2_signature == True
            assert quote.permit2_data is not None
            assert quote.transaction_to != ""
            assert quote.transaction_data != ""

    @pytest.mark.asyncio
    async def test_input_validation_invalid_chain(self, enhanced_zerox):
        """Test input validation for unsupported chain."""
        protocol = enhanced_zerox

        with pytest.raises(ProtocolError) as exc_info:
            await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=999999  # Unsupported chain
            )

        assert "not supported on chain" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_input_validation_invalid_address(self, enhanced_zerox):
        """Test input validation for invalid token address."""
        protocol = enhanced_zerox

        with pytest.raises(ValidationError) as exc_info:
            await protocol.get_indicative_price(
                sell_token="invalid_address",
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1
            )

        assert "Invalid address format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_input_validation_invalid_amount(self, enhanced_zerox):
        """Test input validation for invalid sell amount."""
        protocol = enhanced_zerox

        with pytest.raises(ValidationError) as exc_info:
            await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="invalid_amount",
                chain_id=1
            )

        assert "Invalid sell amount format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_input_validation_same_token_swap(self, enhanced_zerox):
        """Test validation prevents swapping token for itself."""
        protocol = enhanced_zerox

        with pytest.raises(ValidationError) as exc_info:
            await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["WETH"][1],  # Same token
                sell_amount="1000000000000000000",
                chain_id=1
            )

        assert "Cannot swap token for itself" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insufficient_liquidity_error(self, enhanced_zerox):
        """Test handling of insufficient liquidity from API."""
        protocol = enhanced_zerox

        insufficient_balance_response = MOCK_QUOTE_RESPONSE.copy()
        insufficient_balance_response["issues"]["balance"] = {
            "token": TEST_TOKENS["WETH"][1],
            "expected": "1000000000000000000",
            "actual": "500000000000000000"
        }

        with patch.object(protocol, '_make_api_request', return_value=insufficient_balance_response):
            with pytest.raises(InsufficientLiquidityError) as exc_info:
                await protocol.get_firm_quote(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1,
                    taker_address=TEST_WALLET
                )

            assert "Insufficient liquidity" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_error_handling_400(self, enhanced_zerox):
        """Test handling of 400 Bad Request from API."""
        protocol = enhanced_zerox

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json.return_value = {"reason": "Invalid parameters"}

        with patch.object(protocol.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(ValidationError) as exc_info:
                await protocol.get_indicative_price(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1
                )

            assert "Invalid parameters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_error_handling_429_rate_limit(self, enhanced_zerox):
        """Test handling of 429 Rate Limit from API."""
        protocol = enhanced_zerox

        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Reset": "60"
        }
        mock_response.json.return_value = {"reason": "Rate limited"}

        with patch.object(protocol.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(RateLimitError) as exc_info:
                await protocol.get_indicative_price(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1
                )

            error = exc_info.value
            assert error.service == "0x"
            assert error.limit == 1000
            assert error.reset_time == 60

    @pytest.mark.asyncio
    async def test_api_error_handling_500_server_error(self, enhanced_zerox):
        """Test handling of 500 Internal Server Error from API."""
        protocol = enhanced_zerox

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json.return_value = {"error": "Internal server error"}

        with patch.object(protocol.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(ProtocolAPIError) as exc_info:
                await protocol.get_indicative_price(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1
                )

            assert exc_info.value.protocol == "0x"
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, enhanced_zerox):
        """Test local rate limiting enforcement."""
        protocol = enhanced_zerox
        protocol._rate_limit = 2  # Low limit for testing

        with patch.object(protocol, '_make_api_request', return_value=MOCK_PRICE_RESPONSE):
            # First two requests should succeed
            await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1
            )

            await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1
            )

            # Third request should be rate limited
            with pytest.raises(RateLimitError):
                await protocol.get_indicative_price(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1
                )

    @pytest.mark.asyncio
    async def test_permit2_signature_preparation(self, enhanced_zerox):
        """Test preparation of permit2 signature data."""
        protocol = enhanced_zerox

        with patch.object(protocol, '_make_api_request', return_value=MOCK_QUOTE_RESPONSE):
            quote = await protocol.get_firm_quote(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1,
                taker_address=TEST_WALLET
            )

            signature_data = protocol.prepare_permit2_signature_data(quote)

            assert signature_data is not None
            assert "types" in signature_data
            assert "domain" in signature_data
            assert "message" in signature_data
            assert signature_data["primaryType"] == "PermitTransferFrom"

    @pytest.mark.asyncio
    async def test_apply_permit2_signature(self, enhanced_zerox):
        """Test applying permit2 signature to quote."""
        protocol = enhanced_zerox

        with patch.object(protocol, '_make_api_request', return_value=MOCK_QUOTE_RESPONSE):
            quote = await protocol.get_firm_quote(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1,
                taker_address=TEST_WALLET
            )

            original_data = quote.transaction_data
            test_signature = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12"

            updated_quote = protocol.apply_permit2_signature(quote, test_signature)

            assert updated_quote.transaction_data != original_data
            assert len(updated_quote.transaction_data) > len(original_data)
            assert test_signature[2:] in updated_quote.transaction_data

    @pytest.mark.asyncio
    async def test_transaction_simulation(self, enhanced_zerox):
        """Test basic transaction simulation."""
        protocol = enhanced_zerox

        with patch.object(protocol, '_make_api_request', return_value=MOCK_QUOTE_RESPONSE):
            quote = await protocol.get_firm_quote(
                sell_token=TEST_TOKENS["WETH"][1],
                buy_token=TEST_TOKENS["USDC"][1],
                sell_amount="1000000000000000000",
                chain_id=1,
                taker_address=TEST_WALLET
            )

            simulation = await protocol.simulate_transaction(quote, TEST_WALLET)

            assert simulation["success"] == True
            assert "gas_estimate" in simulation
            assert "warnings" in simulation
            assert len(simulation["warnings"]) > 0  # Should have allowance/signature warnings

    def test_performance_stats_tracking(self, enhanced_zerox):
        """Test performance statistics tracking."""
        protocol = enhanced_zerox

        # Add some mock request times
        protocol._request_times = [0.5, 0.8, 0.3, 1.2, 0.6]
        protocol._error_count = 2

        stats = protocol.get_performance_stats()

        assert "average_response_time" in stats
        assert "max_response_time" in stats
        assert "total_requests" in stats
        assert "error_count" in stats
        assert stats["total_requests"] == 5
        assert stats["error_count"] == 2
        assert stats["average_response_time"] == 0.68

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, enhanced_zerox):
        """Test circuit breaker activation and recovery."""
        protocol = enhanced_zerox

        # Configure circuit breaker with low threshold
        protocol.price_circuit_breaker.failure_threshold = 2
        protocol.price_circuit_breaker.recovery_timeout = 1

        # Mock consecutive API failures
        with patch.object(protocol, '_make_api_request') as mock_request:
            mock_request.side_effect = ProtocolAPIError("0x", "/price", 500)

            # First failure
            with pytest.raises(ProtocolAPIError):
                await protocol.get_indicative_price(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1
                )

            # Second failure should open circuit breaker
            with pytest.raises(ProtocolAPIError):
                await protocol.get_indicative_price(
                    sell_token=TEST_TOKENS["WETH"][1],
                    buy_token=TEST_TOKENS["USDC"][1],
                    sell_amount="1000000000000000000",
                    chain_id=1
                )

            # Circuit breaker should now be OPEN
            assert protocol.price_circuit_breaker.state == "OPEN"

    @pytest.mark.asyncio
    async def test_multi_chain_support(self, enhanced_zerox):
        """Test multi-chain support across different networks."""
        protocol = enhanced_zerox

        # Test Base chain
        with patch.object(protocol, '_make_api_request', return_value=MOCK_PRICE_RESPONSE):
            base_quote = await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][8453],
                buy_token=TEST_TOKENS["USDC"][8453],
                sell_amount="1000000000000000000",
                chain_id=8453
            )

            assert base_quote.chain_id == 8453

        # Test Arbitrum chain
        with patch.object(protocol, '_make_api_request', return_value=MOCK_PRICE_RESPONSE):
            arb_quote = await protocol.get_indicative_price(
                sell_token=TEST_TOKENS["WETH"][42161],
                buy_token=TEST_TOKENS["USDC"][42161],
                sell_amount="1000000000000000000",
                chain_id=42161
            )

            assert arb_quote.chain_id == 42161

    @pytest.mark.asyncio
    async def test_get_supported_tokens(self, enhanced_zerox):
        """Test getting supported tokens for a chain."""
        protocol = enhanced_zerox

        mock_tokens_response = {
            "records": [
                {
                    "address": TEST_TOKENS["WETH"][1],
                    "symbol": "WETH",
                    "name": "Wrapped Ether",
                    "decimals": 18
                },
                {
                    "address": TEST_TOKENS["USDC"][1],
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "decimals": 6
                }
            ]
        }

        with patch.object(protocol, '_make_api_request', return_value=mock_tokens_response):
            tokens = await protocol.get_supported_tokens(chain_id=1)

            assert len(tokens) == 2
            assert tokens[0]["symbol"] == "WETH"
            assert tokens[1]["symbol"] == "USDC"

    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test proper session cleanup."""
        protocol = ZeroXEnhanced()

        with patch('app.protocols.zerox_enhanced.config_manager') as mock_config_manager:
            mock_config = AsyncMock()
            mock_config.api_keys = {"default": "test_api_key"}
            mock_config.supported_chains = {1}
            mock_config.api_endpoints = {"1": "https://api.0x.org"}
            mock_config_manager.get_
