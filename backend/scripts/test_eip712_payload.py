#!/usr/bin/env python3
"""
EIP-712 Payload Verification Test
Validates that X402Adapter generates correct EIP-712 typed data for frontend signing
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.protocols.x402_adapter import X402Adapter, X402PaymentRequirements

async def test_eip712_payload():
    """Test EIP-712 payload generation"""
    print("=" * 80)
    print("EIP-712 PAYLOAD VERIFICATION")
    print("=" * 80)
    print()
    
    # Test for Cronos Testnet
    print("Testing Cronos Testnet (devUSDC.e)")
    print("-" * 80)
    
    adapter = X402Adapter("cronos-testnet")
    
    # Create mock payment requirements
    payment_requirements = X402PaymentRequirements(
        scheme="exact",
        network="cronos-testnet",
        payTo="0x1234567890123456789012345678901234567890",
        asset="0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",  # devUSDC.e
        maxAmountRequired="1000000",  # 1 USDC (6 decimals)
        maxTimeoutSeconds=300
    )
    
    # Generate unsigned payload
    payload = await adapter.create_unsigned_payment_payload(
        payment_requirements,
        amount_usdc=1.0
    )
    
    print("\n📋 Generated EIP-712 Payload Structure:")
    print(json.dumps(payload, indent=2))
    
    # Validate structure
    print("\n✓ Validating Payload Structure:")
    
    checks = [
        ("Has 'domain'", "domain" in payload),
        ("Has 'types'", "types" in payload),
        ("Has 'primaryType'", "primaryType" in payload),
        ("Has 'message'", "message" in payload),
        ("Has 'metadata'", "metadata" in payload),
        
        # Domain checks
        ("Domain has 'name'", "name" in payload["domain"]),
        ("Domain has 'version'", "version" in payload["domain"]),
        ("Domain has 'chainId'", "chainId" in payload["domain"]),
        ("Domain has 'verifyingContract'", "verifyingContract" in payload["domain"]),
        
        # Chain ID is correct
        ("Chain ID is 338 (Cronos Testnet)", payload["domain"]["chainId"] == 338),
        
        # Types structure
        ("Types has 'EIP712Domain'", "EIP712Domain" in payload["types"]),
        ("Types has 'TransferWithAuthorization'", "TransferWithAuthorization" in payload["types"]),
        
        # Primary type is correct
        ("PrimaryType is TransferWithAuthorization", payload["primaryType"] == "TransferWithAuthorization"),
        
        # Message structure
        ("Message has 'to'", "to" in payload["message"]),
        ("Message has 'value'", "value" in payload["message"]),
        ("Message has 'validAfter'", "validAfter" in payload["message"]),
        ("Message has 'validBefore'", "validBefore" in payload["message"]),
        ("Message has 'nonce'", "nonce" in payload["message"]),
        
        # Value is correctly converted (1 USDC = 1,000,000 in 6 decimals)
        ("Value is 1000000 (1 USDC)", payload["message"]["value"] == 1000000),
        
        # Metadata
        ("Metadata has 'scheme'", "scheme" in payload["metadata"]),
        ("Metadata has 'network'", "network" in payload["metadata"]),
        ("Metadata has 'asset'", "asset" in payload["metadata"]),
        ("Metadata has 'amount_atomic'", "amount_atomic" in payload["metadata"]),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, result in checks:
        if result:
            print(f"  ✅ {check_name}")
            passed += 1
        else:
            print(f"  ❌ {check_name}")
            failed += 1
    
    print(f"\nValidation: {passed}/{passed + failed} checks passed")
    
    # Now test Ethereum mainnet (MNEE)
    print("\n" + "=" * 80)
    print("Testing Ethereum Mainnet (MNEE)")
    print("-" * 80)
    
    adapter_eth = X402Adapter("ethereum-mainnet")
    
    payment_requirements_eth = X402PaymentRequirements(
        scheme="exact",
        network="ethereum-mainnet",
        payTo="0x1234567890123456789012345678901234567890",
        asset="0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF",  # MNEE
        maxAmountRequired="100000",  # 1 MNEE (5 decimals)
        maxTimeoutSeconds=300
    )
    
    payload_eth = await adapter_eth.create_unsigned_payment_payload(
        payment_requirements_eth,
        amount_usdc=1.0
    )
    
    print("\n📋 Generated EIP-712 Payload for Ethereum:")
    print(json.dumps(payload_eth, indent=2))
    
    print("\n✓ Validating Ethereum Payload:")
    
    checks_eth = [
        ("Chain ID is 1 (Ethereum)", payload_eth["domain"]["chainId"] == 1),
        ("Stablecoin symbol in metadata", payload_eth["metadata"]["asset"] == "0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF"),
        ("Network is ethereum-mainnet", payload_eth["metadata"]["network"] == "ethereum-mainnet"),
    ]
    
    eth_passed = 0
    eth_failed = 0
    
    for check_name, result in checks_eth:
        if result:
            print(f"  ✅ {check_name}")
            eth_passed += 1
        else:
            print(f"  ❌ {check_name}")
            eth_failed += 1
    
    print(f"\nEthereum Validation: {eth_passed}/{eth_passed + eth_failed} checks passed")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_checks = passed + failed + eth_passed + eth_failed
    total_passed = passed + eth_passed
    
    print(f"\nTotal Checks: {total_checks}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_checks - total_passed}")
    print(f"Success Rate: {(total_passed/total_checks)*100:.1f}%")
    
    if total_checks == total_passed:
        print("\n✅ EIP-712 PAYLOAD STRUCTURE IS CORRECT")
        print("\n📝 Ready for Frontend Integration:")
        print("  - Frontend receives EIP-712 payload with domain, types, message, and metadata")
        print("  - Frontend passes to wagmi signTypedData() method")
        print("  - Signature is returned for backend settlement")
        return 0
    else:
        print("\n❌ PAYLOAD VALIDATION FAILED - Fix structure before frontend integration")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_eip712_payload())
    exit(exit_code)
