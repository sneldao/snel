#!/usr/bin/env python3
"""Test script for x402 automation features."""

import sys
import os
sys.path.append('backend')

from app.services.processors.x402_processor import X402Processor
from app.models.unified_models import UnifiedCommand, CommandType, AgentType
import asyncio

async def test_automation():
    """Test x402 automation command processing."""
    processor = X402Processor()
    
    test_cases = [
        {
            "name": "Portfolio Rebalancing",
            "command": "setup monthly portfolio rebalancing with 50 USDC budget",
            "expected_type": "portfolio_rebalancing"
        },
        {
            "name": "Yield Farming", 
            "command": "setup weekly 100 USDC for yield farming when APY > 15%",
            "expected_type": "yield_farming"
        },
        {
            "name": "Conditional Trading",
            "command": "pay 20 USDC to buy ETH when price drops below 3000",
            "expected_type": "conditional_trading"
        },
        {
            "name": "General Automation",
            "command": "setup automated DeFi service with 25 USDC",
            "expected_type": "general_automation"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} Test ===")
        
        command = UnifiedCommand(
            command=test_case['command'],
            command_type=CommandType.X402_PAYMENT,
            agent_type=AgentType.TRANSFER,
            wallet_address='0x123',
            chain_id=338,  # Cronos testnet
            user_name='test_user'
        )
        
        try:
            result = await processor.process(command)
            print(f"✅ Success: {result.success}")
            print(f"📝 Content Preview: {result.content[:150]}...")
            
            if result.metadata:
                automation_type = result.metadata.get('automation_type', 'None')
                budget = result.metadata.get('budget', 'None')
                asset = result.metadata.get('asset', 'None')
                print(f"🤖 Automation Type: {automation_type}")
                print(f"💰 Budget: {budget} {asset}")
                
                # Verify expected automation type
                if automation_type == test_case['expected_type']:
                    print(f"✅ Automation type matches expected: {automation_type}")
                else:
                    print(f"❌ Automation type mismatch. Expected: {test_case['expected_type']}, Got: {automation_type}")
            else:
                print("❌ No metadata returned")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n=== Network Suggestion Test ===")
    # Test network suggestion for non-Cronos chain
    command = UnifiedCommand(
        command="pay agent 10 USDC for API calls",
        command_type=CommandType.X402_PAYMENT,
        agent_type=AgentType.TRANSFER,
        wallet_address='0x123',
        chain_id=1,  # Ethereum mainnet (not supported)
        user_name='test_user'
    )
    
    try:
        result = await processor.process(command)
        print(f"✅ Success: {result.success}")
        print(f"📝 Content Preview: {result.content[:150]}...")
        if "Cronos EVM" in result.content:
            print("✅ Correctly suggests switching to Cronos")
        else:
            print("❌ Does not suggest Cronos network")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_automation())