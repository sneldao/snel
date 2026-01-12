#!/usr/bin/env python3
"""
Test script for x402 automation features
Tests the enhanced automation commands for the Cronos x402 hackathon.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.parser.unified_parser import unified_parser
from app.services.processors.x402_processor import X402Processor
from app.models.unified_models import CommandType

async def test_automation_commands():
    """Test the new automation-focused x402 commands."""
    
    print("🤖 Testing X402 Automation Features for Cronos Hackathon\n")
    
    # Test commands that should trigger x402 automation
    test_commands = [
        "setup monthly portfolio rebalancing with 50 USDC budget",
        "pay 20 USDC to rebalance when my ETH allocation drops below 30%",
        "setup weekly 100 USDC for yield farming when APY > 15%",
        "create automated bridge 200 USDC monthly to polygon",
        "pay agent 10 USDC for API calls",
        "setup recurring payment of 50 USDC to supplier.eth"
    ]
    
    processor = X402Processor()
    
    for i, command in enumerate(test_commands, 1):
        print(f"Test {i}: {command}")
        print("-" * 50)
        
        # Parse command
        command_type, details = unified_parser.parse_command(command)
        print(f"Parsed as: {command_type}")
        
        if command_type == CommandType.X402_PAYMENT:
            # Create unified command
            unified_command = unified_parser.create_unified_command(
                command=command,
                chain_id=338,  # Cronos testnet
                wallet_address="0x1234567890123456789012345678901234567890"
            )
            
            # Process with x402 processor
            try:
                response = await processor.process(unified_command)
                print(f"Status: {response.status}")
                print(f"Agent Type: {response.agent_type}")
                print(f"Content Preview: {response.content[:200]}...")
                
                if response.metadata:
                    print(f"Automation Type: {response.metadata.get('automation_type', 'N/A')}")
                    print(f"Budget: {response.metadata.get('budget', 'N/A')} {response.metadata.get('asset', 'N/A')}")
                    print(f"Network: {response.metadata.get('network', 'N/A')}")
                
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"Not recognized as X402 command (got {command_type})")
        
        print("\n")

async def test_health_check():
    """Test x402 service health check."""
    print("🏥 Testing X402 Service Health Check\n")
    
    try:
        from app.protocols.x402_adapter import check_x402_service_health
        
        # Test both networks
        for network in ["cronos-testnet", "cronos-mainnet"]:
            print(f"Checking {network}...")
            is_healthy = await check_x402_service_health(network)
            print(f"Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
            print()
            
    except Exception as e:
        print(f"Health check failed: {e}")

async def main():
    """Run all tests."""
    print("=" * 60)
    print("X402 AUTOMATION TEST SUITE")
    print("=" * 60)
    print()
    
    await test_health_check()
    await test_automation_commands()
    
    print("=" * 60)
    print("Tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())