#!/usr/bin/env python3
"""
Simulate the exact scenario from the user's screenshot
"""
import asyncio
import os
from app.core.parser.unified_parser import unified_parser
from app.models.unified_models import CommandType, UnifiedCommand
from app.services.processors.contextual_processor import ContextualProcessor

async def simulate_conversation():
    """Simulate the conversation from the screenshot"""
    
    print("=" * 80)
    print("🎭 Simulating User Conversation")
    print("=" * 80)
    print()
    
    # Initialize processor
    processor = ContextualProcessor(
        brian_client=None,
        settings=None,
        protocol_registry=None,
        gmp_service=None,
        price_service=None
    )
    
    # Simulate the greeting
    print("User: gm")
    greeting_cmd = unified_parser.create_unified_command(
        command="gm",
        wallet_address="0x123",
        chain_id=8453,  # Base
        user_name="papa",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    print(f"Detected Type: {greeting_cmd.command_type.value}")
    print()
    
    # Simulate the privacy question
    print("User: what privacy features do you enable?")
    privacy_cmd = unified_parser.create_unified_command(
        command="what privacy features do you enable?",
        wallet_address="0x123",
        chain_id=8453,
        user_name="papa",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    print(f"Detected Type: {privacy_cmd.command_type.value}")
    
    # Check if it would be AI-classified
    if privacy_cmd.command_type == CommandType.UNKNOWN:
        print("Status: Will be AI-classified as CONTEXTUAL_QUESTION ✅")
        print()
        print("Expected Response (Concise):")
        print("-" * 80)
        print("""I enable privacy bridging to Zcash with shielded transactions that hide your
addresses, amounts, and history using zero-knowledge proofs. You can bridge
assets with commands like "bridge 100 USDC to zcash".""")
    elif privacy_cmd.command_type == CommandType.BRIDGE_TO_PRIVACY:
        print("Status: ❌ INCORRECTLY classified as BRIDGE_TO_PRIVACY")
        print("This is a question, not a bridge command!")
    else:
        print(f"Status: Classified as {privacy_cmd.command_type.value}")
    
    print()
    print("=" * 80)
    print()
    
    # Test a few more privacy-related queries
    test_queries = [
        "tell me about your privacy features",
        "how do you keep transactions private?",
        "what privacy do you support?",
        "can you make my transactions anonymous?"
    ]
    
    print("📋 Additional Privacy Question Tests:")
    print("-" * 80)
    for query in test_queries:
        cmd = unified_parser.create_unified_command(
            command=query,
            wallet_address="0x123",
            chain_id=8453,
            user_name="papa"
        )
        
        is_correct = cmd.command_type != CommandType.BRIDGE_TO_PRIVACY
        status = "✅" if is_correct else "❌"
        
        print(f"{status} '{query}'")
        print(f"   → {cmd.command_type.value}")
        print()

if __name__ == "__main__":
    asyncio.run(simulate_conversation())
