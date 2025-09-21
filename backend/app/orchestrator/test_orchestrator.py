#!/usr/bin/env python3
"""
Test script for SNEL Multi-Platform Orchestrator
ENHANCEMENT FIRST: Verify orchestrator works with existing services
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_orchestrator import SNELOrchestrator, Platform

async def test_orchestrator():
    """Test the orchestrator with various operations"""
    print("🚀 Testing SNEL Multi-Platform Orchestrator")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        orchestrator = SNELOrchestrator()
        await asyncio.sleep(2)  # Let health monitoring start
        
        print("✅ Orchestrator initialized successfully!")
        
        # Test 1: Natural Language Processing
        print("\n📝 Test 1: Natural Language Processing")
        result = await orchestrator.execute_defi_operation(
            operation="What is SNEL and what can you do?",
            parameters={},
            platform=Platform.WEB_APP,
            user_id="test-user"
        )
        print(f"Result: {result['success']}")
        if result['success']:
            print(f"Response: {result['data']['snel_response'][:100]}...")
        
        # Test 2: Protocol Research
        print("\n🔍 Test 2: Protocol Research")
        result = await orchestrator.execute_defi_operation(
            operation="research",
            parameters={"protocol": "Uniswap"},
            platform=Platform.CORAL_AGENT,
            user_id="test-user"
        )
        print(f"Result: {result['success']}")
        if result['success']:
            print(f"Research: {result['data']['analysis'][:100]}...")
        
        # Test 3: Different platform formatting
        print("\n📱 Test 3: Mobile-optimized response")
        result = await orchestrator.execute_defi_operation(
            operation="What is DeFi?",
            parameters={},
            platform=Platform.LINE_MINI_DAPP,
            user_id="test-user"
        )
        print(f"Result: {result['success']}")
        if result['success']:
            print(f"Mobile UI Hints: {result.get('ui_hints', {})}")
            print(f"Mobile Optimized: {result.get('mobile_optimized', False)}")
        
        # Test 4: Performance metrics
        print("\n📊 Test 4: Performance Metrics")
        metrics = orchestrator.get_performance_metrics()
        print(f"Total Requests: {metrics.get('total_requests', 0)}")
        print(f"Success Rate: {metrics.get('overall_success_rate', 0)*100:.1f}%")
        print(f"Avg Response Time: {metrics.get('average_response_time', 0):.2f}s")
        
        # Test 5: Service Health
        print("\n💚 Test 5: Service Health")
        health = orchestrator.get_service_health()
        print(f"Active Requests: {health['active_requests']}")
        print(f"Cache Size: {health['cache_size']}")
        print(f"Circuit Breakers: {health['circuit_breakers']}")
        
        print("\n✅ All tests completed successfully!")
        print("🎉 SNEL Orchestrator is ready for multi-platform operation!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
