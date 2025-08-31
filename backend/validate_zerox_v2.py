#!/usr/bin/env python3
"""
Simple validation script for 0x Protocol v2 implementation.
Tests core functionality without requiring external API keys.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

try:
    from app.protocols.zerox_v2 import ZeroXProtocol, SwapQuote
    from app.protocols.permit2_handler import Permit2Handler, Permit2Data
    from app.core.errors import ProtocolError, ValidationError, RateLimitError
    from app.core.config_manager import ProtocolConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the backend directory")
    sys.exit(1)

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def test(self, name: str, passed: bool, message: str = ""):
        status = "✅" if passed else "❌"
        test_line = f"{status} {name}: {message}"
        self.tests.append(test_line)
        print(f"  {test_line}")  # Print immediately for debugging
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*30}")
        print(f"SECTION: {self.passed}/{total} passed")
        print(f"{'='*30}")
        return self.failed == 0

def test_imports():
    """Test that all required modules can be imported."""
    results = TestResults()

    try:
        from app.protocols.zerox_v2 import ZeroXProtocol
        results.test("ZeroXProtocol import", True, "Successfully imported")
    except Exception as e:
        results.test("ZeroXProtocol import", False, str(e))

    try:
        from app.protocols.permit2_handler import Permit2Handler
        results.test("Permit2Handler import", True, "Successfully imported")
    except Exception as e:
        results.test("Permit2Handler import", False, str(e))

    try:
        import aiohttp
        results.test("aiohttp import", True, "Successfully imported")
    except Exception as e:
        results.test("aiohttp import", False, str(e))

    try:
        import aioredis
        results.test("aioredis import", True, "Successfully imported")
    except Exception as e:
        results.test("aioredis import", False, str(e))

    return results

def test_permit2_handler():
    """Test Permit2Handler functionality."""
    results = TestResults()

    try:
        handler = Permit2Handler()
        results.test("Permit2Handler initialization", True, "Handler created")
    except Exception as e:
        results.test("Permit2Handler initialization", False, str(e))
        return results

    # Test contract address validation
    try:
        valid = handler.validate_permit2_contract(1, "0x000000000022d473030f116ddee9f6b43ac78ba3")
        results.test("Contract address validation (valid)", valid, "Permit2 address recognized")

        invalid = handler.validate_permit2_contract(1, "0x1234567890123456789012345678901234567890")
        results.test("Contract address validation (invalid)", not invalid, "Invalid address rejected")
    except Exception as e:
        results.test("Contract address validation", False, str(e))

    # Test signature format validation
    try:
        valid_sig = "0x" + "a" * 130  # 65 bytes = 130 hex chars
        is_valid, _ = handler.validate_signature_format(valid_sig)
        results.test("Signature format validation (valid)", is_valid, "130 char signature accepted")

        invalid_sig = "0x" + "a" * 64  # Too short
        is_valid, _ = handler.validate_signature_format(invalid_sig)
        results.test("Signature format validation (invalid)", not is_valid, "Short signature rejected")
    except Exception as e:
        results.test("Signature format validation", False, str(e))

    # Test transaction data concatenation
    try:
        original = "0x1234"
        signature = "0x" + "a" * 130
        result = handler.concat_transaction_data(original, signature)

        expected_min_length = len(original) + len(signature)  # Should be at least original + signature
        actual_length = len(result)

        results.test("Transaction concatenation", actual_length >= expected_min_length,
                    f"Result length: {actual_length}, expected >= {expected_min_length}")
    except Exception as e:
        results.test("Transaction concatenation", False, str(e))

    return results

async def test_protocol_initialization():
    """Test ZeroXProtocol initialization without API keys."""
    results = TestResults()

    try:
        protocol = ZeroXProtocol()
        results.test("Protocol instance creation", True, "ZeroXProtocol created")
    except Exception as e:
        results.test("Protocol instance creation", False, str(e))
        return results

    # Test properties
    try:
        name = protocol.name
        results.test("Protocol name property", name == "0x", f"Name: {name}")
    except Exception as e:
        results.test("Protocol name property", False, str(e))

    # Test initialization without config (should fail gracefully)
    try:
        await protocol.initialize()
        results.test("Initialization without config", False, "Should have failed")
    except Exception as e:
        if "ProtocolError" in str(type(e)) or "configuration" in str(e).lower():
            results.test("Initialization without config", True, "Properly failed with configuration error")
        else:
            results.test("Initialization without config", False, f"Unexpected error type: {e}")

    try:
        await protocol.close()
        results.test("Protocol cleanup", True, "Close method worked")
    except Exception as e:
        results.test("Protocol cleanup", False, str(e))

    return results

def test_validation_methods():
    """Test validation helper methods."""
    results = TestResults()

    try:
        protocol = ZeroXProtocol()

        # Test address validation
        try:
            protocol._validate_address("0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a")
            results.test("Address validation (valid)", True, "Valid address accepted")
        except Exception as e:
            results.test("Address validation (valid)", False, str(e))

        try:
            protocol._validate_address("invalid")
            results.test("Address validation (invalid)", False, "Should have failed")
        except ValidationError:
            results.test("Address validation (invalid)", True, "Invalid address rejected")
        except Exception as e:
            results.test("Address validation (invalid)", False, f"Wrong error type: {e}")

        # Test swap parameter validation - skip to avoid logger conflict
        try:
            # Mock the config to avoid chain validation
            protocol.config = type('MockConfig', (), {'supported_chains': {1}})()
            protocol._validate_swap_params(
                "0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B",  # USDC
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                "1000000",  # 1 USDC
                1  # Ethereum
            )
            results.test("Swap param validation (valid)", True, "Valid params accepted")
        except Exception as e:
            results.test("Swap param validation (valid)", False, str(e))

        try:
            protocol._validate_swap_params("", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "1000000", 1)
            results.test("Swap param validation (empty token)", False, "Should have failed")
        except ValidationError:
            results.test("Swap param validation (empty token)", True, "Empty token rejected")
        except Exception as e:
            results.test("Swap param validation (empty token)", False, f"Wrong error type: {e}")

    except Exception as e:
        results.test("Validation methods setup", False, str(e))

    return results

def test_circuit_breakers():
    """Test circuit breaker functionality."""
    results = TestResults()

    try:
        protocol = ZeroXProtocol()

        # Test circuit breaker exists
        cb = protocol.price_circuit_breaker
        results.test("Circuit breaker exists", cb is not None, "Price circuit breaker found")

        # Test circuit breaker properties
        results.test("Circuit breaker name", cb.name == "0x_price", f"Name: {cb.name}")
        results.test("Circuit breaker threshold", cb.failure_threshold == 3, f"Threshold: {cb.failure_threshold}")

    except Exception as e:
        results.test("Circuit breaker test", False, str(e))

    return results

async def test_rate_limiting():
    """Test rate limiting functionality."""
    results = TestResults()

    try:
        protocol = ZeroXProtocol()

        # Mock config for testing
        from unittest.mock import MagicMock
        mock_config = MagicMock()
        mock_config.rate_limits = {"requests_per_minute": 2}
        protocol.config = mock_config

        # Test rate limiting logic
        protocol._request_count = 0
        await protocol._check_rate_limits()  # Should pass
        results.test("Rate limiting (under limit)", True, "Request allowed")

        protocol._request_count = 3  # Over limit
        try:
            await protocol._check_rate_limits()
            results.test("Rate limiting (over limit)", False, "Should have been blocked")
        except Exception as e:
            if "rate limit" in str(e).lower() or "RateLimitError" in str(type(e)):
                results.test("Rate limiting (over limit)", True, "Request blocked by rate limit")
            else:
                results.test("Rate limiting (over limit)", False, f"Unexpected error: {e}")

    except Exception as e:
        results.test("Rate limiting test", False, str(e))

    return results

def test_data_models():
    """Test data model classes."""
    results = TestResults()

    try:
        from datetime import datetime, timedelta

        # Test Permit2Data
        permit2_data = Permit2Data(
            permit_type="Permit2",
            hash="0xabcdef",
            eip712={},
            signature_deadline=int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
            nonce="123"
        )
        results.test("Permit2Data creation", True, "Permit2Data created successfully")
        results.test("Permit2Data properties", permit2_data.permit_type == "Permit2", "Properties accessible")

        # Test SwapQuote
        quote = SwapQuote(
            buy_amount="1000000000000000000",
            sell_amount="1000000",
            buy_token="ETH",
            sell_token="USDC",
            price=1000.0,
            estimated_price_impact=0.1,
            gas_estimate=150000,
            gas_price="20000000000",
            sources=[],
            allowance_target="0x000000000022d473030f116ddee9f6b43ac78ba3",
            transaction_data={},
            permit2_data=permit2_data
        )
        results.test("SwapQuote creation", True, "SwapQuote created successfully")
        results.test("SwapQuote permit2 integration", quote.permit2_data is not None, "Permit2 data attached")

    except Exception as e:
        results.test("Data models test", False, str(e))

    return results

async def run_all_tests():
    """Run all validation tests."""
    print("🔍 SNEL 0x Protocol v2 Validation")
    print("=" * 60)

    all_results = []

    print("\n📦 Testing Imports...")
    result1 = test_imports()
    all_results.append(result1)
    result1.summary()

    print("\n🔐 Testing Permit2Handler...")
    result2 = test_permit2_handler()
    all_results.append(result2)
    result2.summary()

    print("\n⚡ Testing Protocol Initialization...")
    result3 = await test_protocol_initialization()
    all_results.append(result3)
    result3.summary()

    print("\n✅ Testing Validation Methods...")
    result4 = test_validation_methods()
    all_results.append(result4)
    result4.summary()

    print("\n🔄 Testing Circuit Breakers...")
    result5 = test_circuit_breakers()
    all_results.append(result5)
    result5.summary()

    print("\n⏱️ Testing Rate Limiting...")
    result6 = await test_rate_limiting()
    all_results.append(result6)
    result6.summary()

    print("\n📊 Testing Data Models...")
    result7 = test_data_models()
    all_results.append(result7)
    result7.summary()

    # Summary
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed

    print(f"\n{'='*60}")
    print(f"🎯 OVERALL RESULTS: {total_passed}/{total_tests} tests passed")

    if total_failed == 0:
        print("✅ ALL TESTS PASSED! 0x v2 implementation is working correctly.")
        print("\n🚀 Ready to proceed with:")
        print("   • Real API integration testing")
        print("   • Performance optimization")
        print("   • Production deployment")
    else:
        print(f"❌ {total_failed} tests failed. Please review the issues above.")
        print("\n🔧 Next steps:")
        print("   • Fix failing imports or dependencies")
        print("   • Review error handling logic")
        print("   • Check configuration setup")

    print(f"{'='*60}")

    return total_failed == 0

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)
