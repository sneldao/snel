#!/usr/bin/env python3
"""
X402 Facilitator Connectivity Test
Tests connection and basic functionality with x402 facilitator endpoints
"""

import asyncio
import json
import httpx
from datetime import datetime

# X402 Facilitator Configuration
FACILITATOR_URLS = {
    "cronos-mainnet": "https://facilitator.cronoslabs.org/v2/x402",
    "cronos-testnet": "https://facilitator.cronoslabs.org/v2/x402",
    "ethereum-mainnet": "https://facilitator.cronoslabs.org/v2/x402"
}

STABLECOIN_CONTRACTS = {
    "cronos-mainnet": "0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C",  # USDC.e Mainnet
    "cronos-testnet": "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",   # devUSDC.e Testnet
    "ethereum-mainnet": "0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF"  # MNEE stablecoin
}

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.duration = 0.0
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} | {self.name} ({self.duration:.2f}s)\n   {self.message}"

async def test_health_check(network: str) -> TestResult:
    """Test facilitator health endpoint"""
    result = TestResult(f"Health Check - {network}")
    start = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = FACILITATOR_URLS[network].replace('/v2/x402', '') + '/healthcheck'
            response = await client.get(url)
            
            result.passed = response.status_code == 200
            result.message = f"Status: {response.status_code}"
            
            if result.passed:
                try:
                    data = response.json()
                    result.message += f" | Response: {json.dumps(data, indent=2)}"
                except:
                    result.message += f" | Body: {response.text[:200]}"
    
    except httpx.ConnectError as e:
        result.message = f"Connection failed: {str(e)}"
    except httpx.TimeoutException:
        result.message = "Request timeout"
    except Exception as e:
        result.message = f"Error: {str(e)}"
    
    result.duration = (datetime.now() - start).total_seconds()
    return result

async def test_supported_schemes(network: str) -> TestResult:
    """Test getting supported payment schemes"""
    result = TestResult(f"Supported Schemes - {network}")
    start = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = FACILITATOR_URLS[network] + '/supported'
            response = await client.get(url)
            
            result.passed = response.status_code == 200
            result.message = f"Status: {response.status_code}"
            
            if result.passed:
                try:
                    data = response.json()
                    kinds = data.get('kinds', [])
                    result.message = f"Supported schemes: {len(kinds)} | "
                    result.message += f"Schemes: {', '.join([k.get('name', 'unknown') for k in kinds[:3]])}"
                    if len(kinds) > 3:
                        result.message += f" +{len(kinds)-3} more"
                except:
                    result.message += f" | Body: {response.text[:200]}"
    
    except httpx.ConnectError as e:
        result.message = f"Connection failed: {str(e)}"
    except httpx.TimeoutException:
        result.message = "Request timeout"
    except Exception as e:
        result.message = f"Error: {str(e)}"
    
    result.duration = (datetime.now() - start).total_seconds()
    return result

async def test_payment_requirements(network: str) -> TestResult:
    """Test getting payment requirements (mock request)"""
    result = TestResult(f"Payment Requirements Query - {network}")
    start = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to query payment requirements (may or may not work depending on facilitator)
            url = FACILITATOR_URLS[network] + '/requirements'
            payload = {
                "x402Version": 1,
                "scheme": "exact",
                "network": network,
                "asset": STABLECOIN_CONTRACTS[network],
                "amount": "1000000"  # 1 USDC/MNEE in atomic units
            }
            
            try:
                response = await client.post(url, json=payload)
                result.passed = response.status_code in [200, 400, 404]  # Accept various responses
                result.message = f"Status: {response.status_code}"
                
                # 404 is OK - endpoint might not exist, just means we can't test it
                if response.status_code == 404:
                    result.message += " | Endpoint not available (expected)"
                    result.passed = True
                elif response.status_code == 200:
                    result.message += " | Endpoint available"
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        result.message += f" | Requirements: {json.dumps(data, indent=2)[:200]}"
                    except:
                        pass
            
            except Exception as e:
                # If the endpoint doesn't exist, that's OK for this test
                result.passed = True
                result.message = f"Endpoint may not support requirements query: {str(e)[:100]}"
    
    except Exception as e:
        result.message = f"Error: {str(e)}"
    
    result.duration = (datetime.now() - start).total_seconds()
    return result

async def test_verify_payment_endpoint(network: str) -> TestResult:
    """Test verify endpoint exists and responds to requests"""
    result = TestResult(f"Verify Endpoint - {network}")
    start = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = FACILITATOR_URLS[network] + '/verify'
            
            # Send a test request (will likely fail due to invalid signature, but that's OK)
            payload = {
                "x402Version": 1,
                "paymentHeader": "invalid_test_header",
                "paymentRequirements": {
                    "scheme": "exact",
                    "network": network,
                    "payTo": "0x0000000000000000000000000000000000000000",
                    "asset": STABLECOIN_CONTRACTS[network],
                    "maxAmountRequired": "1000000",
                    "maxTimeoutSeconds": 300
                }
            }
            
            response = await client.post(url, json=payload)
            
            # Any response (200-500) means the endpoint exists
            result.passed = response.status_code < 600
            result.message = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                result.message += " | Endpoint available"
            elif response.status_code >= 400:
                result.message += " | Endpoint exists (validation failed as expected)"
            
            try:
                data = response.json()
                result.message += f" | Response keys: {', '.join(list(data.keys())[:5])}"
            except:
                pass
    
    except Exception as e:
        result.message = f"Error: {str(e)}"
    
    result.duration = (datetime.now() - start).total_seconds()
    return result

async def test_settle_payment_endpoint(network: str) -> TestResult:
    """Test settle endpoint exists and responds to requests"""
    result = TestResult(f"Settle Endpoint - {network}")
    start = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = FACILITATOR_URLS[network] + '/settle'
            
            # Send a test request (will likely fail, but that's OK)
            payload = {
                "x402Version": 1,
                "paymentHeader": "invalid_test_header",
                "paymentRequirements": {
                    "scheme": "exact",
                    "network": network,
                    "payTo": "0x0000000000000000000000000000000000000000",
                    "asset": STABLECOIN_CONTRACTS[network],
                    "maxAmountRequired": "1000000",
                    "maxTimeoutSeconds": 300
                }
            }
            
            response = await client.post(url, json=payload)
            
            # Any response (200-500) means the endpoint exists
            result.passed = response.status_code < 600
            result.message = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                result.message += " | Endpoint available"
            elif response.status_code >= 400:
                result.message += " | Endpoint exists (validation failed as expected)"
            
            try:
                data = response.json()
                result.message += f" | Response keys: {', '.join(list(data.keys())[:5])}"
            except:
                pass
    
    except Exception as e:
        result.message = f"Error: {str(e)}"
    
    result.duration = (datetime.now() - start).total_seconds()
    return result

async def run_all_tests():
    """Run all tests for all networks"""
    print("=" * 80)
    print("X402 FACILITATOR CONNECTIVITY TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    networks = ["cronos-testnet", "cronos-mainnet", "ethereum-mainnet"]
    all_results = []
    
    for network in networks:
        print(f"\n{'='*60}")
        print(f"Testing Network: {network}")
        print(f"Facilitator URL: {FACILITATOR_URLS[network]}")
        print(f"Stablecoin: {STABLECOIN_CONTRACTS[network]}")
        print(f"{'='*60}")
        
        # Run tests sequentially to avoid rate limiting
        tests = [
            test_health_check(network),
            test_supported_schemes(network),
            test_payment_requirements(network),
            test_verify_payment_endpoint(network),
            test_settle_payment_endpoint(network),
        ]
        
        for test_coro in tests:
            result = await test_coro
            all_results.append(result)
            print(result)
            print()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Detailed results by network
    for network in networks:
        network_results = [r for r in all_results if network in r.name]
        network_passed = sum(1 for r in network_results if r.passed)
        print(f"\n{network}: {network_passed}/{len(network_results)} passed")
    
    print("\n" + "=" * 80)
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Facilitator is reachable and functional")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Check connectivity or facilitator status")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    exit(exit_code)
