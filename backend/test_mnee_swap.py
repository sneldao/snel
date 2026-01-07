#!/usr/bin/env python3
"""Test MNEE swap functionality"""

import asyncio
import sys
import os
from decimal import Decimal

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.swap_service import swap_service
from services.price_service import price_service

async def test_mnee_price_lookup():
    """Test MNEE price lookup"""
    print("💰 Testing MNEE Price Lookup...")
    
    # Test MNEE price (should use USDC price as fallback)
    mnee_price = await price_service.get_token_price("MNEE")
    print(f"MNEE price: ${mnee_price}")
    
    if mnee_price and mnee_price > 0:
        print("✅ MNEE price lookup working")
        return True
    else:
        print("❌ MNEE price lookup failed")
        return False

async def test_usd_to_mnee_conversion():
    """Test USD to MNEE conversion"""
    print("🔄 Testing USD to MNEE Conversion...")
    
    usd_amount = Decimal("1.0")
    mnee_amount = await price_service.convert_usd_to_token_amount(usd_amount, "MNEE")
    
    print(f"$1 USD = {mnee_amount} MNEE")
    
    if mnee_amount and mnee_amount > 0:
        print("✅ USD to MNEE conversion working")
        return True
    else:
        print("❌ USD to MNEE conversion failed")
        return False

async def test_mnee_1sat_swap_quote():
    """Test MNEE swap quote on 1Sat Ordinals"""
    print("🔄 Testing MNEE Swap Quote on 1Sat Ordinals...")
    
    try:
        # Test MNEE to MNEE transfer on 1Sat Ordinals (chain 236)
        quote = await swap_service.get_quote(
            from_token_id="mnee",
            to_token_id="mnee", 
            amount=Decimal("10.0"),  # 10 MNEE
            chain_id=236,  # 1Sat Ordinals
            wallet_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Example address
        )
        
        print(f"Quote result: {quote}")
        
        if quote.get("success"):
            print("✅ MNEE swap quote successful on 1Sat Ordinals")
            print(f"Protocol: {quote.get('protocol', 'unknown')}")
            print(f"Network: {quote.get('network', 'unknown')}")
            print(f"Amount: {quote.get('from_amount')} MNEE -> {quote.get('to_amount')} MNEE")
            print(f"Estimated fee: {quote.get('estimated_fee_usd', 'unknown')}")
            print(f"Features: {quote.get('features', [])}")
            return True
        else:
            print(f"❌ MNEE swap quote failed: {quote.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ MNEE swap quote failed with exception: {e}")
        return False

async def test_mnee_ethereum_support():
    """Test MNEE support on Ethereum"""
    print("🔄 Testing MNEE Support on Ethereum...")
    
    try:
        # Test MNEE to MNEE transfer on Ethereum (chain 1)
        quote = await swap_service.get_quote(
            from_token_id="mnee",
            to_token_id="mnee", 
            amount=Decimal("5.0"),  # 5 MNEE
            chain_id=1,  # Ethereum
            wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96c4b4d8b6"  # Example Ethereum address
        )
        
        print(f"Quote result: {quote}")
        
        if quote.get("success"):
            print("✅ MNEE swap quote successful on Ethereum")
            print(f"Protocol: {quote.get('protocol', 'unknown')}")
            print(f"Network: {quote.get('network', 'unknown')}")
            print(f"Amount: {quote.get('from_amount')} MNEE -> {quote.get('to_amount')} MNEE")
            print(f"Estimated fee: {quote.get('estimated_fee_usd', 'unknown')}")
            print(f"Features: {quote.get('features', [])}")
            return True
        else:
            print(f"❌ MNEE swap quote failed: {quote.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ MNEE swap quote failed with exception: {e}")
        return False

async def main():
    """Run all MNEE swap tests"""
    print("🧪 Testing MNEE Swap Functionality")
    print("=" * 50)
    
    tests = [
        test_mnee_price_lookup,
        test_usd_to_mnee_conversion,
        test_mnee_1sat_swap_quote,
        test_mnee_ethereum_support
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
            print()
    
    print("=" * 50)
    if all(results):
        print("🎉 All MNEE swap tests passed!")
        print("✅ MNEE price lookup: Working")
        print("✅ USD conversion: Working") 
        print("✅ Swap quotes: Working")
        print("\n🚀 MNEE swap functionality is ready!")
    else:
        print("❌ Some MNEE swap tests failed")
        print("This might be due to:")
        print("- Network connectivity issues")
        print("- API rate limits")
        print("- Insufficient liquidity for MNEE")
        print("- MNEE contract not deployed on test chains")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)