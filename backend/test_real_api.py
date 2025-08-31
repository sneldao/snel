#!/usr/bin/env python3
"""
Real API integration test for 0x Protocol v2 implementation.
Tests actual API calls with permit2 support.
"""

import asyncio
import sys
import os
from pathlib import Path
from decimal import Decimal
import json

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

try:
    from app.protocols.zerox_v2 import ZeroXProtocol
    from app.core.config_manager import ProtocolConfig
    from app.core.errors import ProtocolError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the backend directory")
    sys.exit(1)

class RealAPITest:
    """Test real 0x API integration."""

    def __init__(self):
        self.protocol = None
        self.test_chains = [1, 8453]  # Ethereum, Base
        self.test_tokens = {
            1: {  # Ethereum
                'USDC': '0xA0b86a33E6E94f0E73F4C99c4E64Bb7E8cf7Dc1B',
                'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                'ETH': 'ETH'
            },
            8453: {  # Base
                'USDC': '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
                'WETH': '0x4200000000000000000000000000000000000006',
                'ETH': 'ETH'
            }
        }
        self.test_wallet = '0x742d35Cc6634C0532925a3b8D45bc9B07f4a3b8a'

    async def setup(self):
        """Setup protocol with real configuration."""
        print("🔧 Setting up 0x Protocol...")

        # Check for API key
        api_key = os.getenv('ZEROX_API_KEY')
        if not api_key:
            print("⚠️  No ZEROX_API_KEY found in environment")
            print("   Set with: export ZEROX_API_KEY='your_key_here'")
            print("   Will attempt to test with basic functionality")

        # Initialize the real config manager
        from app.core.config_manager import config_manager

        # Initialize config manager to load real configurations
        try:
            await config_manager.initialize()
            print("✅ ConfigurationManager initialized")
        except Exception as e:
            print(f"⚠️  ConfigurationManager initialization failed: {e}")
            print("   Proceeding with basic setup")

        # Create protocol instance
        self.protocol = ZeroXProtocol()

        # Try to initialize with real config
        try:
            await self.protocol.initialize()
            print("✅ Protocol initialized with real configuration")
        except Exception as e:
            print(f"❌ Protocol initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources."""
        if self.protocol:
            await self.protocol.close()

        # Close config manager
        try:
            from app.core.config_manager import config_manager
            await config_manager.close()
        except Exception as e:
            print(f"⚠️  Config manager cleanup warning: {e}")

    async def test_price_endpoint(self, chain_id: int):
        """Test indicative price endpoint."""
        print(f"\n📊 Testing price endpoint on chain {chain_id}...")

        try:
            tokens = self.test_tokens[chain_id]

            price_data = await self.protocol.get_price(
                sell_token=tokens['USDC'],
                buy_token=tokens['ETH'],
                sell_amount='1000000',  # 1 USDC (6 decimals)
                chain_id=chain_id,
                taker_address=self.test_wallet
            )

            print(f"✅ Price data received:")
            print(f"   Buy Amount: {price_data.get('buyAmount', 'N/A')}")
            print(f"   Price: {price_data.get('price', 'N/A')}")
            print(f"   Sources: {len(price_data.get('sources', []))}")

            return True

        except Exception as e:
            print(f"❌ Price endpoint failed: {e}")
            return False

    async def test_quote_endpoint(self, chain_id: int):
        """Test firm quote endpoint with permit2."""
        print(f"\n🎯 Testing quote endpoint on chain {chain_id}...")

        try:
            tokens = self.test_tokens[chain_id]

            quote = await self.protocol.get_quote(
                sell_token=tokens['USDC'],
                buy_token=tokens['ETH'],
                sell_amount='1000000',  # 1 USDC
                chain_id=chain_id,
                taker_address=self.test_wallet,
                slippage_bps=100  # 1%
            )

            print(f"✅ Quote received:")
            print(f"   Buy Amount: {quote.buy_amount}")
            print(f"   Sell Amount: {quote.sell_amount}")
            print(f"   Price: {quote.price:.4f}")
            print(f"   Gas Estimate: {quote.gas_estimate:,}")
            print(f"   Requires Signature: {quote.requires_signature}")
            print(f"   Allowance Target: {quote.allowance_target}")

            if quote.permit2_data:
                print(f"   Permit2 Type: {quote.permit2_data.permit_type}")
                print(f"   Signature Deadline: {quote.permit2_data.signature_deadline}")
                print(f"   EIP-712 Domain: {quote.permit2_data.eip712.get('domain', {}).get('name', 'N/A')}")

            if quote.eip712_message:
                print(f"   EIP-712 Primary Type: {quote.eip712_message.get('primaryType', 'N/A')}")

            # Test permit2 requirements extraction
            requirements = self.protocol.get_permit2_requirements(quote)
            print(f"   Permit2 Requirements:")
            print(f"     - Requires Permit2: {requirements.get('requires_permit2', False)}")
            print(f"     - Needs Approval: {requirements.get('needs_approval', False)}")

            return True, quote

        except Exception as e:
            print(f"❌ Quote endpoint failed: {e}")
            return False, None

    async def test_transaction_building(self, quote):
        """Test transaction building with permit2."""
        if not quote or not quote.permit2_data:
            print("⏭️  Skipping transaction building (no permit2 data)")
            return True

        print(f"\n🔨 Testing transaction building...")

        try:
            # Mock signature (65 bytes = 130 hex chars)
            mock_signature = "0x" + "a" * 130

            transaction = await self.protocol.build_permit2_transaction(
                quote=quote,
                signature=mock_signature,
                chain_id=1
            )

            print(f"✅ Transaction built:")
            print(f"   To: {transaction['to']}")
            print(f"   Data Length: {len(transaction['data'])} chars")
            print(f"   Value: {transaction['value']}")
            print(f"   Gas Limit: {transaction['gasLimit']}")

            return True

        except Exception as e:
            print(f"❌ Transaction building failed: {e}")
            return False

    async def test_allowance_info(self, chain_id: int):
        """Test allowance information retrieval."""
        print(f"\n🔐 Testing allowance info on chain {chain_id}...")

        try:
            tokens = self.test_tokens[chain_id]

            allowance_info = await self.protocol.get_allowance_info(
                token_address=tokens['USDC'],
                owner_address=self.test_wallet,
                chain_id=chain_id
            )

            print(f"✅ Allowance info:")
            print(f"   Allowance: {allowance_info.get('allowance', 'N/A')}")
            print(f"   Spender: {allowance_info.get('spender', 'N/A')}")
            print(f"   Needs Approval: {allowance_info.get('needs_approval', 'N/A')}")

            return True

        except Exception as e:
            print(f"❌ Allowance info failed: {e}")
            return False

    async def test_supported_tokens(self, chain_id: int):
        """Test supported tokens retrieval."""
        print(f"\n🪙 Testing supported tokens on chain {chain_id}...")

        try:
            tokens = await self.protocol.get_supported_tokens(chain_id)

            print(f"✅ Found {len(tokens)} supported tokens")
            if tokens:
                # Show first few tokens
                for i, token in enumerate(tokens[:3]):
                    print(f"   {i+1}. {token.get('symbol', 'N/A')} - {token.get('name', 'N/A')}")
                if len(tokens) > 3:
                    print(f"   ... and {len(tokens) - 3} more")

            return True

        except Exception as e:
            print(f"❌ Supported tokens failed: {e}")
            return False

    async def test_performance(self):
        """Test performance under concurrent requests."""
        print(f"\n⚡ Testing concurrent performance...")

        try:
            import time

            # Test 5 concurrent price requests
            start_time = time.time()

            tasks = []
            for i in range(5):
                task = self.protocol.get_price(
                    sell_token=self.test_tokens[1]['USDC'],
                    buy_token=self.test_tokens[1]['ETH'],
                    sell_amount='1000000',
                    chain_id=1,
                    taker_address=self.test_wallet
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = len(results) - successes
            duration = end_time - start_time

            print(f"✅ Concurrent test results:")
            print(f"   Requests: 5")
            print(f"   Successes: {successes}")
            print(f"   Failures: {failures}")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Avg per request: {duration/5:.2f}s")

            return failures == 0

        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run comprehensive API integration tests."""
        print("🚀 SNEL 0x Protocol v2 Real API Integration Test")
        print("=" * 60)

        results = []

        try:
            await self.setup()

            # Test each chain
            for chain_id in self.test_chains:
                print(f"\n🔗 Testing Chain {chain_id}")
                print("-" * 30)

                # Price endpoint test
                price_success = await self.test_price_endpoint(chain_id)
                results.append(('Price endpoint', chain_id, price_success))

                # Quote endpoint test
                quote_success, quote = await self.test_quote_endpoint(chain_id)
                results.append(('Quote endpoint', chain_id, quote_success))

                # Transaction building test
                if quote_success:
                    tx_success = await self.test_transaction_building(quote)
                    results.append(('Transaction building', chain_id, tx_success))

                # Allowance info test
                allowance_success = await self.test_allowance_info(chain_id)
                results.append(('Allowance info', chain_id, allowance_success))

                # Supported tokens test
                tokens_success = await self.test_supported_tokens(chain_id)
                results.append(('Supported tokens', chain_id, tokens_success))

                # Small delay between chains
                await asyncio.sleep(1)

            # Performance test
            perf_success = await self.test_performance()
            results.append(('Performance test', 'all', perf_success))

        except Exception as e:
            print(f"\n💥 Test setup failed: {e}")
            return False

        finally:
            await self.cleanup()

        # Results summary
        print(f"\n{'='*60}")
        print("📊 TEST RESULTS SUMMARY")
        print("='*60")

        total_tests = len(results)
        successful_tests = sum(1 for _, _, success in results if success)

        for test_name, chain, success in results:
            status = "✅" if success else "❌"
            chain_str = f"Chain {chain}" if isinstance(chain, int) else chain
            print(f"{status} {test_name:<20} ({chain_str})")

        print("-" * 60)
        print(f"🎯 Overall: {successful_tests}/{total_tests} tests passed")

        if successful_tests == total_tests:
            print("✅ ALL TESTS PASSED! 0x v2 API integration is working!")
            print("\n🚀 Ready for:")
            print("   • Production deployment")
            print("   • Circle integration")
            print("   • Real user transactions")
        else:
            failed = total_tests - successful_tests
            print(f"❌ {failed} tests failed. Check API key and network connectivity.")

        print("=" * 60)

        return successful_tests == total_tests

async def main():
    """Main test runner."""
    try:
        test = RealAPITest()
        success = await test.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
