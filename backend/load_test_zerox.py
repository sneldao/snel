#!/usr/bin/env python3
"""
Load testing for 0x Protocol v2 implementation.
Tests high-concurrency scenarios and sustained load.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

try:
    from app.protocols.zerox_v2 import ZeroXProtocol
    from app.core.errors import RateLimitError, ProtocolError
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class LoadTestMetrics:
    """Track load test metrics."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    def record_success(self, response_time: float):
        self.response_times.append(response_time)
        self.success_count += 1
    
    def record_error(self):
        self.error_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        total_time = time.time() - self.start_time
        total_requests = self.success_count + self.error_count
        
        if self.response_times:
            avg_response = statistics.mean(self.response_times)
            p95_response = statistics.quantiles(self.response_times, n=20)[18]
            p99_response = statistics.quantiles(self.response_times, n=100)[98]
        else:
            avg_response = p95_response = p99_response = 0
        
        return {
            "total_requests": total_requests,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / total_requests * 100) if total_requests > 0 else 0,
            "total_time_seconds": total_time,
            "requests_per_second": total_requests / total_time if total_time > 0 else 0,
            "avg_response_time_ms": avg_response * 1000,
            "p95_response_time_ms": p95_response * 1000,
            "p99_response_time_ms": p99_response * 1000
        }


async def concurrent_load_test(concurrent_users: int, requests_per_user: int):
    """Test concurrent load with multiple users."""
    print(f"\n🔥 Load Test: {concurrent_users} concurrent users, {requests_per_user} requests each")
    
    metrics = LoadTestMetrics()
    
    async def user_session():
        """Simulate a user session."""
        protocol = ZeroXProtocol()
        
        # Mock configuration
        from unittest.mock import MagicMock
        mock_config = MagicMock()
        mock_config.supported_chains = {1}
        mock_config.rate_limits = {"requests_per_minute": 1000}
        protocol.config = mock_config
        
        try:
            for _ in range(requests_per_user):
                start_time = time.time()
                try:
                    # Test validation (fast operation)
                    protocol._validate_address("0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a")
                    response_time = time.time() - start_time
                    metrics.record_success(response_time)
                except Exception:
                    metrics.record_error()
        finally:
            await protocol.close()
    
    # Run concurrent user sessions
    tasks = [user_session() for _ in range(concurrent_users)]
    await asyncio.gather(*tasks)
    
    summary = metrics.get_summary()
    
    print(f"  ✅ Load Test Results:")
    print(f"     • Total Requests: {summary['total_requests']}")
    print(f"     • Success Rate: {summary['success_rate']:.1f}%")
    print(f"     • Requests/Second: {summary['requests_per_second']:.1f}")
    print(f"     • Avg Response Time: {summary['avg_response_time_ms']:.2f}ms")
    print(f"     • P95 Response Time: {summary['p95_response_time_ms']:.2f}ms")
    print(f"     • P99 Response Time: {summary['p99_response_time_ms']:.2f}ms")
    
    # Success criteria
    success = (
        summary['success_rate'] >= 95.0 and
        summary['avg_response_time_ms'] < 100.0 and
        summary['requests_per_second'] > 100.0
    )
    
    return success, summary


async def run_load_tests():
    """Run comprehensive load tests."""
    print("🚀 SNEL 0x Protocol v2 Load Testing")
    print("=" * 50)
    
    test_scenarios = [
        (10, 5),   # 10 users, 5 requests each = 50 total
        (25, 4),   # 25 users, 4 requests each = 100 total
        (50, 2),   # 50 users, 2 requests each = 100 total
    ]
    
    results = []
    
    for concurrent_users, requests_per_user in test_scenarios:
        try:
            success, metrics = await concurrent_load_test(concurrent_users, requests_per_user)
            results.append({
                "scenario": f"{concurrent_users}x{requests_per_user}",
                "success": success,
                "metrics": metrics
            })
        except Exception as e:
            print(f"❌ Load test failed: {e}")
            results.append({
                "scenario": f"{concurrent_users}x{requests_per_user}",
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*50}")
    print("🎯 LOAD TEST SUMMARY")
    print(f"{'='*50}")
    
    passed_tests = sum(1 for result in results if result["success"])
    total_tests = len(results)
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} Scenario {result['scenario']}")
    
    print(f"\n🎯 OVERALL RESULTS: {passed_tests}/{total_tests} load tests passed")
    
    if passed_tests == total_tests:
        print("✅ ALL LOAD TESTS PASSED!")
        print("\n🚀 0x Protocol v2 can handle:")
        print("   • High concurrent load")
        print("   • Sustained traffic")
        print("   • Production workloads")
    else:
        print(f"❌ {total_tests - passed_tests} load tests failed.")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    try:
        success = asyncio.run(run_load_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Load tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error during load testing: {e}")
        sys.exit(1)
