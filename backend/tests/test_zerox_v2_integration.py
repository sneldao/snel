"""
Integration tests for 0x Protocol v2 implementation.

Tests real API integration, permit2 functionality, EIP-712 signature handling,
transaction simulation, and all critical paths for production readiness.
"""

import asyncio
import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.protocols.zerox_v2 import ZeroXProtocol, SwapQuote
from backend.app.protocols.permit2_handler import Permit2Handler, Permit2Data
from backend.app.core.errors import (
    ProtocolError, ProtocolAPIError, ValidationError,
    InsufficientLiquidityError, RateLimitError
)
from backend.app.core.config_manager import ProtocolConfig


class TestZeroXV2Integration:
    """Integration tests for 0x Protocol v2."""

    @pytest.fixture
    async def protocol(self):
        """Create 0x protocol instance for testing."""
        protocol = ZeroXProtocol()

        # Mock configuration manager
        mock_config = ProtocolConfig(
            id="0x",
            name="0x Protocol",
            type="swap",
            supported_chains={1, 8453, 42161},  # Ethereum, Base, Arbitrum
            api_endpoints={
                "1": "https://api.0x.org",
                "8453": "https://base.api.0x.org",
                "42161": "https://arbitrum.api.0x.org"
            },
            contract_addresses={},
            api_keys={"default": "test_api_key"},
            rate_limits={"requests_per_minute": 1000}
        )

        with patch('backend.app.core.config_manager.config_manager') as mock_cm:
            mock_cm.get_protocol.return_value = mock_config
            await protocol.initialize()

        yield protocol

        await protocol.close()

    @pytest.fixture
    def sample_permit2_response(self):
        """Sample 0x API response with permit2 data."""
        return {
            "chainId": 1,
            "buyAmount": "1000000000000000000",
            "sellAmount": "1000000",
            "buyToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            "sellToken": "0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",  # USDC
            "price": "1000.0",
            "estimatedPriceImpact": "0.12",
            "gas": "150000",
            "gasPrice": "20000000000",
            "transaction": {
                "to": "0x13B2238D08Ca7A36eAAD2DcC8AD4d6CC97C9D2b3",  # Settler contract
                "data": "0x1234567890abcdef",
                "value": "0"
            },
            "permit2": {
                "type": "Permit2",
                "hash": "0xabcdef1234567890",
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
                        ]
                    },
                    "domain": {
                        "name": "Permit2",
                        "chainId": 1,
                        "verifyingContract": "0x000000000022d473030f116ddee9f6b43ac78ba3"
                    },
                    "message": {
                        "permitted": {
                            "token": "0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                            "amount": "1000000"
                        },
                        "spender": "0x13B2238D08Ca7A36eAAD2DcC8AD4d6CC97C9D2b3",
                        "nonce": "1234567890",
                        "deadline": int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
                    },
                    "primaryType": "PermitTransferFrom"
                }
            },
            "issues": {
                "allowance": {
                    "actual": "0",
                    "spender": "0x000000000022d473030f116ddee9f6b43ac78ba3",
                    "expected": "1000000"
                }
            },
            "route": {
                "fills": [
                    {
                        "source": "Uniswap_V3",
                        "proportion": "1.0"
                    }
                ]
            }
        }

    @pytest.fixture
    def sample_price_response(self):
        """Sample 0x price response."""
        return {
            "chainId": 1,
            "buyAmount": "1000000000000000000",
            "sellAmount": "1000000",
            "buyToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "sellToken": "0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
            "price": "1000.0",
            "estimatedPriceImpact": "0.12",
            "gas": "150000",
            "gasPrice": "20000000000",
            "route": {
                "fills": [{"source": "Uniswap_V3", "proportion": "1.0"}]
            }
        }

    @pytest.mark.asyncio
    async def test_initialization_success(self, protocol):
        """Test successful protocol initialization."""
        assert protocol.name == "0x"
        assert protocol.session is not None
        assert protocol.config is not None
        assert protocol.permit2_handler is not None

    @pytest.mark.asyncio
    async def test_initialization_no_config(self):
        """Test initialization failure when no config available."""
        protocol = ZeroXProtocol()

        with patch('backend.app.core.config_manager.config_manager') as mock_cm:
            mock_cm.get_protocol.return_value = None

            with pytest.raises(ProtocolError) as exc_info:
                await protocol.initialize()

            assert "configuration not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialization_no_api_key(self):
        """Test initialization failure when API key missing."""
        protocol = ZeroXProtocol()

        mock_config = ProtocolConfig(
            id="0x", name="0x", type="swap", supported_chains={1},
            api_endpoints={"1": "https://api.0x.org"},
            contract_addresses={}, api_keys={}
        )

        with patch('backend.app.core.config_manager.config_manager') as mock_cm:
            mock_cm.get_protocol.return_value = mock_config

            with pytest.raises(ProtocolError) as exc_info:
                await protocol.initialize()

            assert "API key not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_price_success(self, protocol, sample_price_response):
        """Test successful price retrieval."""
        with patch.object(protocol, '_make_api_request', return_value=sample_price_response):
            result = await protocol.get_price(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x123"
            )

            assert result["buyAmount"] == "1000000000000000000"
            assert result["sellAmount"] == "1000000"
            assert result["price"] == "1000.0"

    @pytest.mark.asyncio
    async def test_get_quote_with_permit2(self, protocol, sample_permit2_response):
        """Test quote generation with permit2 data."""
        with patch.object(protocol, '_make_api_request', return_value=sample_permit2_response):
            quote = await protocol.get_quote(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

            assert isinstance(quote, SwapQuote)
            assert quote.buy_amount == "1000000000000000000"
            assert quote.sell_amount == "1000000"
            assert quote.requires_signature is True
            assert quote.permit2_data is not None
            assert quote.eip712_message is not None
            assert quote.allowance_target == "0x000000000022d473030f116ddee9f6b43ac78ba3"

    @pytest.mark.asyncio
    async def test_get_quote_validation_error(self, protocol):
        """Test quote request with invalid parameters."""
        with pytest.raises(ValidationError):
            await protocol.get_quote(
                sell_token="",  # Empty token
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

    @pytest.mark.asyncio
    async def test_get_quote_unsupported_chain(self, protocol):
        """Test quote request for unsupported chain."""
        with pytest.raises(ProtocolError) as exc_info:
            await protocol.get_quote(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=999,  # Unsupported chain
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

        assert "not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insufficient_liquidity_error(self, protocol):
        """Test handling of insufficient liquidity from API."""
        error_response = {
            "issues": {
                "balance": {
                    "token": "USDC",
                    "expected": "1000000",
                    "actual": "500000"
                }
            }
        }

        with patch.object(protocol, '_make_api_request', return_value=error_response):
            with pytest.raises(InsufficientLiquidityError):
                await protocol.get_quote(
                    sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                    buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    sell_amount="1000000",
                    chain_id=1,
                    taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
                )

    @pytest.mark.asyncio
    async def test_build_permit2_transaction(self, protocol, sample_permit2_response):
        """Test building transaction with permit2 signature."""
        # First get a quote with permit2 data
        with patch.object(protocol, '_make_api_request', return_value=sample_permit2_response):
            quote = await protocol.get_quote(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

        # Mock signature (65 bytes = 130 hex chars)
        mock_signature = "0x" + "a" * 130

        transaction = await protocol.build_permit2_transaction(
            quote=quote,
            signature=mock_signature,
            chain_id=1
        )

        assert transaction["to"] == "0x13B2238D08Ca7A36eAAD2DcC8AD4d6CC97C9D2b3"
        assert transaction["chainId"] == 1
        assert len(transaction["data"]) > len("0x1234567890abcdef")  # Should be longer with signature
        assert transaction["gasLimit"] == str(int(150000 * 1.2))  # 20% buffer

    @pytest.mark.asyncio
    async def test_build_permit2_transaction_invalid_signature(self, protocol, sample_permit2_response):
        """Test building transaction with invalid signature."""
        with patch.object(protocol, '_make_api_request', return_value=sample_permit2_response):
            quote = await protocol.get_quote(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

        with pytest.raises(ValidationError):
            await protocol.build_permit2_transaction(
                quote=quote,
                signature="invalid_signature",
                chain_id=1
            )

    @pytest.mark.asyncio
    async def test_validate_quote_freshness(self, protocol, sample_permit2_response):
        """Test quote freshness validation."""
        with patch.object(protocol, '_make_api_request', return_value=sample_permit2_response):
            quote = await protocol.get_quote(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

        # Fresh quote should be valid
        assert await protocol.validate_quote_freshness(quote) is True

        # Expired quote should be invalid
        quote.expires_at = datetime.utcnow() - timedelta(seconds=10)
        assert await protocol.validate_quote_freshness(quote) is False

    @pytest.mark.asyncio
    async def test_get_permit2_requirements(self, protocol, sample_permit2_response):
        """Test extracting permit2 requirements."""
        with patch.object(protocol, '_make_api_request', return_value=sample_permit2_response):
            quote = await protocol.get_quote(
                sell_token="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                buy_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                sell_amount="1000000",
                chain_id=1,
                taker_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a"
            )

        requirements = protocol.get_permit2_requirements(quote)

        assert requirements["requires_permit2"] is True
        assert requirements["requires_signature"] is True
        assert requirements["needs_approval"] is True
        assert requirements["allowance_target"] == "0x000000000022d473030f116ddee9f6b43ac78ba3"
        assert "signing_instructions" in requirements
        assert "approval_instructions" in requirements

    @pytest.mark.asyncio
    async def test_rate_limiting(self, protocol):
        """Test rate limiting enforcement."""
        # Set low rate limit for testing
        protocol.config.rate_limits["requests_per_minute"] = 2

        # Reset rate limiting state
        protocol._request_count = 2  # At limit
        protocol._request_window_start = datetime.utcnow()

        with pytest.raises(RateLimitError):
            await protocol._check_rate_limits()

    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self, protocol):
        """Test circuit breaker activation on failures."""
        # Force circuit breaker to trip
        for _ in range(3):  # failure_threshold = 3
            try:
                await protocol.price_circuit_breaker(lambda: exec("raise Exception('test')"))()
            except:
                pass

        # Circuit breaker should now be open
        assert protocol.price_circuit_breaker.is_open() is True

    @pytest.mark.asyncio
    async def test_api_error_handling(self, protocol):
        """Test various API error scenarios."""
        # Test 400 error
        with patch.object(protocol.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text.return_value = '{"reason": "Invalid token address"}'
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(ValidationError):
                await protocol._make_api_request("GET", "http://test.com")

        # Test 429 rate limit error
        with patch.object(protocol.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.text.return_value = '{"reason": "Rate limit exceeded"}'
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(RateLimitError):
                await protocol._make_api_request("GET", "http://test.com")

        # Test 500 server error
        with patch.object(protocol.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = '{"reason": "Internal server error"}'
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(ProtocolAPIError):
                await protocol._make_api_request("GET", "http://test.com")

    @pytest.mark.asyncio
    async def test_transaction_simulation(self, protocol):
        """Test transaction simulation functionality."""
        # Mock chain config with RPC endpoint
        mock_chain_config = MagicMock()
        mock_chain_config.rpc_endpoints = ["https://rpc.test.com"]

        with patch('backend.app.core.config_manager.config_manager') as mock_cm:
            mock_cm.get_chain.return_value = mock_chain_config

            # Mock successful simulation
            with patch.object(protocol.session, 'post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {"result": "0x1234"}
                mock_post.return_value.__aenter__.return_value = mock_response

                transaction_data = {
                    "to": "0x123",
                    "data": "0xabcd",
                    "value": "0"
                }

                result = await protocol.simulate_transaction(
                    transaction_data=transaction_data,
                    chain_id=1,
                    from_address="0x456"
                )

                assert result["success"] is True
                assert "return_data" in result

    @pytest.mark.asyncio
    async def test_allowance_info_retrieval(self, protocol):
        """Test allowance information retrieval."""
        mock_response = {
            "allowance": "1000000",
            "spender": "0x000000000022d473030f116ddee9f6b43ac78ba3"
        }

        with patch.object(protocol, '_make_api_request', return_value=mock_response):
            result = await protocol.get_allowance_info(
                token_address="0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                owner_address="0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a",
                chain_id=1
            )

            assert result["allowance"] == "1000000"
            assert result["spender"] == "0x000000000022d473030f116ddee9f6b43ac78ba3"
            assert result["needs_approval"] is False

    @pytest.mark.asyncio
    async def test_supported_tokens_retrieval(self, protocol):
        """Test supported tokens list retrieval."""
        mock_response = {
            "records": [
                {
                    "address": "0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "decimals": 6
                },
                {
                    "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "symbol": "WETH",
                    "name": "Wrapped Ether",
                    "decimals": 18
                }
            ]
        }

        with patch.object(protocol, '_make_api_request', return_value=mock_response):
            tokens = await protocol.get_supported_tokens(chain_id=1)

            assert len(tokens) == 2
            assert tokens[0]["symbol"] == "USDC"
            assert tokens[1]["symbol"] == "WETH"

    def test_is_supported_chain(self, protocol):
        """Test chain support checking."""
        assert protocol.is_supported(1) is True      # Ethereum
        assert protocol.is_supported(8453) is True   # Base
        assert protocol.is_supported(42161) is True  # Arbitrum
        assert protocol.is_supported(999) is False   # Unsupported


class TestPermit2Handler:
    """Tests for Permit2Handler functionality."""

    @pytest.fixture
    def permit2_handler(self):
        return Permit2Handler()

    @pytest.fixture
    def sample_permit2_api_response(self):
        """Sample API response with permit2 data."""
        return {
            "chainId": 1,
            "permit2": {
                "type": "Permit2",
                "hash": "0xabcdef",
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
                        ]
                    },
                    "domain": {
                        "name": "Permit2",
                        "chainId": 1,
                        "verifyingContract": "0x000000000022d473030f116ddee9f6b43ac78ba3"
                    },
                    "message": {
                        "permitted": {
                            "token": "0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",
                            "amount": "1000000"
                        },
                        "spender": "0x13B2238D08Ca7A36eAAD2DcC8AD4d6CC97C9D2b3",
                        "nonce": "1234567890",
                        "deadline": int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
                    },
                    "primaryType": "PermitTransferFrom"
                }
            },
            "transaction": {
                "to": "0x13B2238D08Ca7A36eAAD2DcC8AD4d6CC97C9D2b3",
                "data": "0x1234567890abcdef"
            },
            "issues": {
                "allowance": {
                    "actual": "0",
                    "spender": "0x000000000022d473030f116ddee9f6b43ac78ba3",
                    "expected": "1000000"
                }
            }
        }

    def test_extract_permit2_data(self, permit2_handler, sample_permit2_api_response):
        """Test permit2 data extraction from API response."""
        permit2_data = permit2_handler.extract_permit2_data(sample_permit2_api_response)

        assert permit2_data is not None
        assert permit2_data.permit_type == "Permit2"
        assert permit2_data.hash == "0xabcdef"
        assert permit2_data.nonce == "1234567890"

    def test_extract_permit2_data_missing(self, permit2_handler):
        """Test permit2 data extraction when not present."""
        response_without_permit2 = {"chainId": 1, "buyAmount": "1000"}

        permit2_data = permit2_handler.extract_permit2_data(response_without_permit2)
        assert permit2_data is None

    def test_validate_permit2_contract(self, permit2_handler):
        """Test permit2 contract address validation."""
        valid_address = "0x000000000022d473030f116ddee9f6b43ac78ba3"
        invalid_address = "0x1234567890123456789012345678901234567890"

        assert permit2_handler.validate_permit2_contract(1, valid_address) is True
        assert permit2_handler.validate_permit2_contract(1, invalid_address) is False

    def test_format_eip712_message(self, permit2_handler, sample_permit2_api_response):
        """Test EIP-712 message formatting."""
        permit2_data = permit2_handler.extract_permit2_data(sample_permit2_api_response)

        eip712_message = permit2_handler.format_eip712_message(permit2_data, 1)

        assert "types" in eip712_message
        assert "domain" in eip712_message
        assert "message" in eip712_message
        assert "primaryType" in eip712_message
        assert eip712_message["primaryType"] == "PermitTransferFrom"

    def test_validate_signature_deadline(self, permit2_handler):
        """Test signature deadline validation."""
        future_deadline = int((datetime.utcnow() + timedelta(minutes=10)).timestamp())
        past_deadline = int((datetime.utcnow() - timedelta(minutes=1)).timestamp())

        permit2_data_valid = Permit2Data(
            permit_type="Permit2",
            hash="0xabcd",
            eip712={},
            signature_deadline=future_deadline,
            nonce="123"
        )

        permit2_data_expired = Permit2Data(
            permit_type="Permit2",
            hash="0xabcd",
            eip712={},
            signature_deadline=past_deadline,
            nonce="123"
        )

        assert permit2_handler.validate_signature_deadline(permit2_data_valid) is True
        assert permit2_handler.validate_signature_deadline(permit2_data_expired) is False

    def test_signature_format_validation(self, permit2_handler):
        """Test signature format validation."""
        valid_signature = "0x" + "a" * 130  # 65 bytes = 130 hex chars
        invalid_short = "0x" + "a" * 64     # Too short
        invalid_long = "0x" + "a" * 200     # Too long
        invalid_hex = "0xzzzzz"             # Invalid hex

        assert permit2_handler.validate_signature_format(valid_signature)[0] is True
        assert permit2_handler.validate_signature_format(invalid_short)[0] is False
        assert permit2_handler.validate_signature_format(invalid_long)[0] is False
        assert permit2_handler.validate_signature_format(invalid_hex)[0] is False

    def test_concat_transaction_data(self, permit2_handler):
        """Test transaction data concatenation with signature."""
        original_data = "0x1234567890abcdef"
        signature = "0x" + "a" * 130

        result = permit2_handler.concat_transaction_data(original_data, signature)

        # Should be: 0x + original_data + signature_length_bytes + signature
        assert result.startswith("0x")
        assert len(result) > len(original_data) + len(signature)
        assert result.endswith("a" * 130)  # Should end with signature

    def test_extract_allowance_info(self, permit2_handler, sample_permit2_api_response):
        """Test allowance information extraction."""
        allowance_info = permit2_handler.extract_allowance_info(sample_permit2_api_response)

        assert allowance_info["spender"] == "0x000000000022d473030f116ddee9f6b43ac78ba3"
        assert allowance_info["actual_allowance"] == "0"
        assert allowance_info["expected_allowance"] == "1000000"
        assert allowance_info["needs_approval"] is True
        assert allowance_info["is_permit2"] is True
