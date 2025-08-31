"""
Circle CCTP V2 Service Validation Tests
Following SNEL testing excellence standards with comprehensive coverage.
"""
import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircleCCTPValidator:
    """Comprehensive validator for Circle CCTP V2 service following SNEL patterns."""
    
    def __init__(self):
        self.test_results = []
        self.performance_metrics = {}
        self.start_time = None
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive Circle CCTP V2 validation tests."""
        logger.info("🚀 Starting Circle CCTP V2 Service Validation")
        self.start_time = time.time()
        
        test_methods = [
            self.test_service_initialization,
            self.test_chain_support_validation,
            self.test_cross_chain_quote_functionality,
            self.test_comprehensive_error_handling,
            self.test_rate_limiting_and_circuit_breaker,
            self.test_fee_estimation_with_caching,
            self.test_performance_benchmarks
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
                self.test_results.append({
                    "test": test_method.__name__,
                    "status": "PASS",
                    "message": "Test completed successfully"
                })
            except Exception as e:
                logger.error(f"❌ {test_method.__name__} failed: {e}")
                self.test_results.append({
                    "test": test_method.__name__,
                    "status": "FAIL", 
                    "message": str(e)
                })
        
        return await self.generate_final_report()
        
    async def test_service_initialization(self):
        """Test Circle CCTP service initialization and configuration."""
        logger.info("🔧 Testing service initialization...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test initialization
        await circle_cctp_service.initialize()
        
        # Verify configuration loaded
        assert circle_cctp_service.config is not None, "Configuration not loaded"
        assert circle_cctp_service.session is not None, "HTTP session not initialized"
        
        # Verify supported chains
        supported_chains = circle_cctp_service.get_supported_chains()
        assert len(supported_chains) >= 7, f"Expected at least 7 chains, got {len(supported_chains)}"
        
        # Verify key chains are supported
        required_chains = [1, 42161, 8453, 137, 43114]  # ETH, ARB, BASE, POLYGON, AVAX
        for chain_id in required_chains:
            assert chain_id in supported_chains, f"Chain {chain_id} not supported"
            
        logger.info("✅ Service initialization test passed")

    async def test_chain_support_validation(self):
        """Test chain support validation and token compatibility."""
        logger.info("🔗 Testing chain support validation...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test supported chains
        supported_chains = [1, 42161, 8453, 137, 43114, 59144]
        for chain_id in supported_chains:
            assert circle_cctp_service.is_chain_supported(chain_id), f"Chain {chain_id} should be supported"
            
        # Test unsupported chains
        unsupported_chains = [999, 56, 250]  # Random, BSC, Fantom
        for chain_id in unsupported_chains:
            assert not circle_cctp_service.is_chain_supported(chain_id), f"Chain {chain_id} should not be supported"
            
        # Test USDC token support
        for chain_id in supported_chains:
            is_supported = await circle_cctp_service.is_token_supported("USDC", chain_id)
            assert is_supported, f"USDC should be supported on chain {chain_id}"
            
        # Test non-USDC token rejection
        for chain_id in supported_chains[:3]:  # Test first 3 chains
            is_supported = await circle_cctp_service.is_token_supported("WETH", chain_id)
            assert not is_supported, f"WETH should not be supported on chain {chain_id}"
            
        logger.info("✅ Chain support validation test passed")

    async def test_cross_chain_quote_functionality(self):
        """Test cross-chain quote generation and validation."""
        logger.info("💱 Testing cross-chain quote functionality...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test valid cross-chain quote
        quote = await circle_cctp_service.get_cross_chain_quote(
            from_token="USDC",
            to_token="USDC", 
            amount=Decimal("100.0"),
            from_chain_id=1,  # Ethereum
            to_chain_id=42161,  # Arbitrum
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
        
        # Verify quote structure
        assert quote.get("success") == True, "Quote should be successful"
        assert quote.get("protocol") == "cctp_v2", "Protocol should be cctp_v2"
        assert quote.get("from_token") == "USDC", "From token should be USDC"
        assert quote.get("to_token") == "USDC", "To token should be USDC"
        assert "steps" in quote, "Quote should contain transaction steps"
        assert len(quote["steps"]) >= 2, "Should have at least 2 steps (approve + burn)"
        
        # Verify transaction steps
        steps = quote["steps"]
        assert steps[0]["type"] == "approve", "First step should be approve"
        assert steps[1]["type"] == "burn_and_mint", "Second step should be burn_and_mint"
        
        logger.info("✅ Cross-chain quote functionality test passed")

    async def test_comprehensive_error_handling(self):
        """Test comprehensive error handling scenarios."""
        logger.info("🚨 Testing comprehensive error handling...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test invalid token pair
        quote = await circle_cctp_service.get_cross_chain_quote(
            from_token="WETH",
            to_token="USDC",
            amount=Decimal("100.0"),
            from_chain_id=1,
            to_chain_id=42161,
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
        assert "error" in quote, "Should return error for non-USDC tokens"
        
        # Test unsupported chain
        quote = await circle_cctp_service.get_cross_chain_quote(
            from_token="USDC",
            to_token="USDC",
            amount=Decimal("100.0"),
            from_chain_id=999,  # Unsupported
            to_chain_id=42161,
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
        assert "error" in quote, "Should return error for unsupported chain"
        
        # Test invalid recipient address
        quote = await circle_cctp_service.get_cross_chain_quote(
            from_token="USDC",
            to_token="USDC",
            amount=Decimal("100.0"),
            from_chain_id=1,
            to_chain_id=42161,
            wallet_address="invalid_address"
        )
        assert "error" in quote, "Should return error for invalid address"
        
        # Test same chain transfer
        quote = await circle_cctp_service.get_cross_chain_quote(
            from_token="USDC",
            to_token="USDC",
            amount=Decimal("100.0"),
            from_chain_id=1,
            to_chain_id=1,  # Same chain
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        )
        assert "error" in quote, "Should return error for same chain transfer"
        
        logger.info("✅ Comprehensive error handling test passed")

    async def test_rate_limiting_and_circuit_breaker(self):
        """Test rate limiting and circuit breaker functionality."""
        logger.info("⚡ Testing rate limiting and circuit breaker...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test rate limiting doesn't break normal operations
        start_time = time.time()
        
        # Make multiple requests within rate limit
        for i in range(3):
            quote = await circle_cctp_service.get_cross_chain_quote(
                from_token="USDC",
                to_token="USDC",
                amount=Decimal("10.0"),
                from_chain_id=1,
                to_chain_id=42161,
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
            )
            # Should succeed or fail gracefully
            assert isinstance(quote, dict), f"Request {i+1} should return a dict"
            
        elapsed_time = time.time() - start_time
        
        # Verify rate limiting is working (should take some time for multiple requests)
        assert elapsed_time >= 0.1, "Rate limiting should introduce some delay"
        
        # Test circuit breaker state tracking
        assert hasattr(circle_cctp_service, '_api_state'), "Should have API state tracking"
        
        logger.info("✅ Rate limiting and circuit breaker test passed")

    async def test_fee_estimation_with_caching(self):
        """Test fee estimation with caching functionality."""
        logger.info("💰 Testing fee estimation with caching...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test fee estimation
        fee1 = await circle_cctp_service._get_transfer_fee(1, 42161, Decimal("100.0"))
        assert isinstance(fee1, str), "Fee should be returned as string"
        assert float(fee1) > 0, "Fee should be positive"
        
        # Test caching - second call should be faster
        start_time = time.time()
        fee2 = await circle_cctp_service._get_transfer_fee(1, 42161, Decimal("100.0"))
        cache_time = time.time() - start_time
        
        assert fee1 == fee2, "Cached fee should match original"
        assert cache_time < 0.1, "Cached call should be fast"
        
        # Test different chain pair
        fee3 = await circle_cctp_service._get_transfer_fee(8453, 137, Decimal("50.0"))
        assert isinstance(fee3, str), "Fee for different chains should be string"
        
        # Verify cache is working
        assert hasattr(circle_cctp_service, '_quote_cache'), "Should have quote cache"
        assert len(circle_cctp_service._quote_cache) > 0, "Cache should contain entries"
        
        logger.info("✅ Fee estimation with caching test passed")

    async def test_performance_benchmarks(self):
        """Test performance benchmarks and response times."""
        logger.info("🚀 Testing performance benchmarks...")
        
        from app.services.circle_cctp_service import circle_cctp_service
        
        # Test quote generation performance
        quote_times = []
        for i in range(5):
            start_time = time.time()
            quote = await circle_cctp_service.get_cross_chain_quote(
                from_token="USDC",
                to_token="USDC",
                amount=Decimal("100.0"),
                from_chain_id=1,
                to_chain_id=42161,
                wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
            )
            elapsed = time.time() - start_time
            quote_times.append(elapsed)
            
        avg_quote_time = sum(quote_times) / len(quote_times)
        max_quote_time = max(quote_times)
        
        # Performance assertions
        assert avg_quote_time < 2.0, f"Average quote time {avg_quote_time:.3f}s should be under 2s"
        assert max_quote_time < 5.0, f"Max quote time {max_quote_time:.3f}s should be under 5s"
        
        # Store performance metrics
        self.performance_metrics.update({
            "avg_quote_time": avg_quote_time,
            "max_quote_time": max_quote_time,
            "quote_samples": len(quote_times)
        })
        
        logger.info(f"✅ Performance benchmarks passed - Avg: {avg_quote_time:.3f}s, Max: {max_quote_time:.3f}s")

    async def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_time = time.time() - self.start_time
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        total_tests = len(self.test_results)
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
                "total_time": f"{total_time:.2f}s"
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "status": "PASS" if passed_tests == total_tests else "FAIL"
        }
        
        # Print summary
        logger.info("=" * 60)
        logger.info("🎯 CIRCLE CCTP V2 VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Tests Passed: {passed_tests}/{total_tests}")
        logger.info(f"⏱️  Total Time: {total_time:.2f}s")
        logger.info(f"🚀 Success Rate: {report['summary']['success_rate']}")
        
        if self.performance_metrics:
            logger.info(f"📊 Avg Quote Time: {self.performance_metrics.get('avg_quote_time', 0):.3f}s")
            
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED - Circle CCTP V2 is PRODUCTION READY!")
        else:
            logger.error("❌ Some tests failed - Review implementation")
            
        return report

async def main():
    """Run Circle CCTP V2 validation tests."""
    validator = CircleCCTPValidator()
    report = await validator.run_all_tests()
    return report

if __name__ == "__main__":
    asyncio.run(main())
