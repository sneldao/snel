#!/usr/bin/env python3
"""
Test script to verify privacy question classification
"""
import asyncio
from app.core.parser.unified_parser import unified_parser
from app.models.unified_models import CommandType

def test_privacy_questions():
    """Test that privacy questions are classified correctly"""
    
    test_cases = [
        # Should be CONTEXTUAL_QUESTION (questions about capabilities)
        ("what privacy features do you enable?", CommandType.CONTEXTUAL_QUESTION),
        ("what privacy features do you support?", CommandType.CONTEXTUAL_QUESTION),
        ("tell me about privacy", CommandType.CONTEXTUAL_QUESTION),
        ("how do you handle privacy?", CommandType.CONTEXTUAL_QUESTION),
        ("what are your privacy capabilities?", CommandType.CONTEXTUAL_QUESTION),
        
        # Should be BRIDGE_TO_PRIVACY (actual bridge intents)
        ("bridge 100 USDC to zcash", CommandType.BRIDGE_TO_PRIVACY),
        ("make my 50 ETH private", CommandType.BRIDGE_TO_PRIVACY),
        ("send 10 USDC privately", CommandType.BRIDGE_TO_PRIVACY),
        ("I want to make 100 USDC private", CommandType.BRIDGE_TO_PRIVACY),
    ]
    
    print("🧪 Testing Privacy Question Classification\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for command, expected_type in test_cases:
        detected_type, details = unified_parser.parse_command(command)
        
        # For questions without specific patterns, they'll be UNKNOWN and need AI classification
        # But they should NOT be classified as BRIDGE_TO_PRIVACY
        if expected_type == CommandType.CONTEXTUAL_QUESTION:
            # These should either be UNKNOWN (will be AI-classified) or a non-bridge type
            is_correct = detected_type != CommandType.BRIDGE_TO_PRIVACY
            status = "✅" if is_correct else "❌"
            
            if is_correct:
                passed += 1
                print(f"{status} '{command}'")
                print(f"   → {detected_type.value} (will be AI-classified as CONTEXTUAL_QUESTION)")
            else:
                failed += 1
                print(f"{status} '{command}'")
                print(f"   → INCORRECTLY classified as {detected_type.value}")
                print(f"   → Expected: NOT {CommandType.BRIDGE_TO_PRIVACY.value}")
        else:
            # These should match exactly
            is_correct = detected_type == expected_type
            status = "✅" if is_correct else "❌"
            
            if is_correct:
                passed += 1
            else:
                failed += 1
                
            print(f"{status} '{command}'")
            print(f"   → {detected_type.value} (expected: {expected_type.value})")
        
        print()
    
    print("=" * 80)
    print(f"\n📊 Results: {passed} passed, {failed} failed\n")
    
    if failed == 0:
        print("✅ All tests passed!")
        return True
    else:
        print(f"❌ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    success = test_privacy_questions()
    exit(0 if success else 1)
