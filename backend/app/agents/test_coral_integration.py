#!/usr/bin/env python3
"""
SNEL Coral Integration Test
ENHANCEMENT FIRST: Test proper Coral Server integration using existing orchestrator
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coral_mcp_adapter import SNELCoralMCPAdapter, CoralEnvironment, get_devmode_connection_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_coral_integration():
    """Test SNEL Coral integration"""
    print("🧪 SNEL Coral Integration Test")
    print("=" * 50)
    
    # Test 1: Environment Detection
    print("\n1. Testing Environment Detection...")
    coral_env = CoralEnvironment.from_env()
    
    print(f"   Agent ID: {coral_env.agent_id}")
    print(f"   Session ID: {coral_env.session_id}")
    print(f"   Runtime: {coral_env.runtime or 'standalone'}")
    print(f"   Orchestrated: {coral_env.is_orchestrated}")
    print(f"   Devmode: {coral_env.is_devmode}")
    
    # Test 2: MCP Adapter Initialization
    print("\n2. Testing MCP Adapter...")
    adapter = SNELCoralMCPAdapter()
    
    try:
        await adapter.initialize()
        print("   ✅ MCP Adapter initialized successfully")
    except Exception as e:
        print(f"   ⚠️ MCP Adapter initialization: {e}")
    
    # Test 3: Health Check
    print("\n3. Testing Health Check...")
    health = await adapter.health_check()
    print(f"   Status: {health.get('status')}")
    print(f"   Agent ID: {health.get('agent_id')}")
    print(f"   Tools Available: {health.get('tools_available')}")
    print(f"   Orchestrator Health: {health.get('orchestrator_health', {}).get('services', 'N/A')}")
    
    # Test 4: Available Tools
    print("\n4. Testing Available Tools...")
    tools = adapter.get_available_tools()
    print(f"   Tool Count: {len(tools)}")
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description'][:50]}...")
    
    # Test 5: Tool Execution (Mock)
    print("\n5. Testing Tool Execution...")
    test_cases = [
        {
            "tool": "general_defi_help",
            "params": {"user_request": "What is DeFi?"}
        },
        {
            "tool": "research_protocol", 
            "params": {"protocol_name": "Uniswap"}
        }
    ]
    
    for test_case in test_cases:
        try:
            result = await adapter.handle_tool_call(
                test_case["tool"], 
                test_case["params"]
            )
            success = result.get('success', False)
            print(f"   {test_case['tool']}: {'✅' if success else '❌'}")
            if not success:
                print(f"     Error: {result.get('error', 'Unknown')}")
        except Exception as e:
            print(f"   {test_case['tool']}: ❌ Exception: {e}")
    
    # Test 6: Devmode URL Generation
    print("\n6. Testing Devmode Support...")
    devmode_url = get_devmode_connection_url()
    print(f"   Devmode URL: {devmode_url}")
    
    # Test 7: Configuration Validation
    print("\n7. Testing Configuration...")
    required_env = ["OPENAI_API_KEY", "BRIAN_API_KEY"]
    for env_var in required_env:
        value = os.getenv(env_var)
        status = "✅" if value else "❌"
        print(f"   {env_var}: {status}")
    
    # Cleanup
    await adapter.shutdown()
    
    print("\n" + "=" * 50)
    print("🎯 Integration Test Complete!")
    print("\nNext Steps:")
    print("1. Configure API keys in .env")
    print("2. Test with Coral Server in devmode")
    print("3. Deploy to production Coral Server")

async def test_devmode_connection():
    """Test devmode connection simulation"""
    print("\n🔗 Testing Devmode Connection Simulation...")
    
    # Set devmode environment
    os.environ["CORAL_CONNECTION_URL"] = get_devmode_connection_url()
    os.environ["CORAL_AGENT_ID"] = "snel-defi-agent"
    os.environ["CORAL_SESSION_ID"] = "test-session"
    
    coral_env = CoralEnvironment.from_env()
    print(f"   Connection URL: {coral_env.connection_url}")
    print(f"   Is Devmode: {coral_env.is_devmode}")
    
    adapter = SNELCoralMCPAdapter()
    
    # Test message processing
    test_message = {
        "type": "tool_call",
        "tool_name": "general_defi_help",
        "parameters": {"user_request": "Hello from Coral!"},
        "call_id": "test-123"
    }
    
    import json
    await adapter._process_mcp_message(json.dumps(test_message))
    
    print("   ✅ Devmode simulation complete")

if __name__ == "__main__":
    asyncio.run(test_coral_integration())
    asyncio.run(test_devmode_connection())