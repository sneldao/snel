#!/usr/bin/env python3
"""
End-to-end test of x402 payment flow through backend API
"""

import asyncio
import httpx
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

async def test_payment_flow():
    print("=" * 80)
    print("X402 PAYMENT FLOW TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API: {API_BASE_URL}")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Check health
        print("1️⃣  Checking x402 health...")
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/x402/health/cronos-testnet")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Health check passed")
                print(f"   📊 Healthy: {health.get('healthy')}")
                print(f"   🌐 Network: {health.get('network')}")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        print()

        # Test 2: Get supported networks
        print("2️⃣  Getting supported networks...")
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/x402/supported-networks")
            if response.status_code == 200:
                networks = response.json()
                print(f"   ✅ Got {len(networks.get('networks', []))} supported networks")
                for net in networks.get('networks', [])[:3]:
                    print(f"      - {net.get('name')} (ID: {net.get('network_id')})")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        print()

        # Test 3: Prepare payment (get EIP-712 payload)
        print("3️⃣  Preparing payment (getting EIP-712 payload)...")
        test_user = "0x742d35Cc6634C0532925a3b844Bc9e7595f42bE7"
        test_recipient = "0x1234567890123456789012345678901234567890"
        test_amount = 1.0

        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/x402/prepare-payment",
                json={
                    "user_address": test_user,
                    "recipient_address": test_recipient,
                    "amount_usdc": test_amount,
                    "network": "cronos-testnet"
                }
            )

            if response.status_code == 200:
                payload = response.json()
                print(f"   ✅ Payment prepared successfully")
                print(f"\n   📋 EIP-712 Payload Structure:")
                print(f"      Domain:")
                print(f"        - name: {payload['domain'].get('name')}")
                print(f"        - chainId: {payload['domain'].get('chainId')}")
                print(f"      Types:")
                types_keys = list(payload['types'].keys())
                print(f"        - {', '.join(types_keys)}")
                print(f"      Message:")
                print(f"        - to: {payload['message'].get('to')}")
                print(f"        - value: {payload['message'].get('value')}")
                print(f"        - validBefore: {payload['message'].get('validBefore')}")
                print(f"      Metadata:")
                print(f"        - scheme: {payload['metadata'].get('scheme')}")
                print(f"        - network: {payload['metadata'].get('network')}")
                
                # Save payload for verification
                with open("/tmp/eip712_payload.json", "w") as f:
                    json.dump(payload, f, indent=2)
                print(f"\n   💾 Payload saved to /tmp/eip712_payload.json")
            else:
                error_detail = response.json() if response.headers.get("content-type") == "application/json" else response.text
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Error: {error_detail}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        print()

        # Test 4: Validate payload structure
        print("4️⃣  Validating payload structure...")
        required_keys = ["domain", "types", "primaryType", "message", "metadata"]
        missing = [k for k in required_keys if k not in payload]
        
        if missing:
            print(f"   ❌ Missing keys: {missing}")
            return False
        
        required_domain_keys = ["name", "version", "chainId", "verifyingContract"]
        missing_domain = [k for k in required_domain_keys if k not in payload["domain"]]
        
        if missing_domain:
            print(f"   ❌ Missing domain keys: {missing_domain}")
            return False

        if payload["domain"]["chainId"] != 338:
            print(f"   ❌ Wrong chainId: {payload['domain']['chainId']} (expected 338)")
            return False

        if payload["primaryType"] != "TransferWithAuthorization":
            print(f"   ❌ Wrong primaryType: {payload['primaryType']}")
            return False

        print(f"   ✅ Payload structure is valid")
        print(f"   ✅ Ready for Wagmi signTypedData()")

        print()
        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("📝 Next Steps:")
        print("   1. Frontend gets this payload")
        print("   2. User signs with Wagmi: signTypedData(payload)")
        print("   3. Frontend submits signature to /api/v1/x402/submit-payment")
        print("   4. Backend submits to facilitator and returns tx hash")
        print()

        return True

if __name__ == "__main__":
    result = asyncio.run(test_payment_flow())
    exit(0 if result else 1)
