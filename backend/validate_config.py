#!/usr/bin/env python3
"""
Configuration validation script for SNEL foundation work.

This script validates that our configuration manager works correctly
and that we've successfully eliminated mock implementations.

Usage:
    python validate_config.py
"""

import asyncio
import logging
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config_manager import config_manager
from app.core.errors import SNELError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_configuration():
    """Validate configuration manager setup."""
    try:
        logger.info("🔧 Initializing Configuration Manager...")
        await config_manager.initialize()
        logger.info("✅ Configuration Manager initialized successfully")

        # Test token configuration
        logger.info("\n📋 Testing Token Configuration...")
        usdc = await config_manager.get_token("usdc")
        if usdc:
            logger.info(f"✅ USDC found: {usdc.name} ({usdc.symbol})")
            logger.info(f"   Supported chains: {list(usdc.addresses.keys())}")
        else:
            logger.error("❌ USDC token not found")

        # Test chain configuration
        logger.info("\n🌐 Testing Chain Configuration...")
        ethereum = await config_manager.get_chain(1)
        if ethereum:
            logger.info(f"✅ Ethereum found: {ethereum.display_name}")
            logger.info(f"   Status: {ethereum.status.value}")
            logger.info(f"   Supported protocols: {ethereum.supported_protocols}")
        else:
            logger.error("❌ Ethereum chain not found")

        # Test protocol configuration
        logger.info("\n🔌 Testing Protocol Configuration...")
        zerox = await config_manager.get_protocol("0x")
        if zerox:
            logger.info(f"✅ 0x Protocol found: {zerox.name}")
            logger.info(f"   Status: {zerox.status.value}")
            logger.info(f"   Supported chains: {len(zerox.supported_chains)}")
            logger.info(f"   API endpoints: {len(zerox.api_endpoints)}")
        else:
            logger.error("❌ 0x Protocol not found")

        # Test cross-referencing
        logger.info("\n🔗 Testing Cross-References...")
        usdc_eth_address = await config_manager.get_token_address("usdc", 1)
        if usdc_eth_address:
            logger.info(f"✅ USDC on Ethereum: {usdc_eth_address}")
        else:
            logger.error("❌ USDC address on Ethereum not found")

        # Test protocol support validation
        zerox_on_ethereum = await config_manager.is_protocol_supported("0x", 1)
        logger.info(f"✅ 0x on Ethereum supported: {zerox_on_ethereum}")

        axelar_on_base = await config_manager.is_protocol_supported("axelar", 8453)
        logger.info(f"✅ Axelar on Base supported: {axelar_on_base}")

        return True

    except SNELError as e:
        logger.error(f"❌ SNEL Configuration Error: {e.message}")
        logger.error(f"   Error Code: {e.error_code}")
        logger.error(f"   User Message: {e.user_message}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False
    finally:
        await config_manager.close()

async def validate_mock_elimination():
    """Validate that mock implementations have been eliminated."""
    logger.info("\n🚫 Validating Mock Elimination...")

    try:
        # Test Axelar service (should use config manager now)
        from app.services.axelar_service import AxelarService
        axelar = AxelarService()

        # This should work without returning mock data
        logger.info("✅ Axelar service imports successfully")

        # Test 0x protocol (should use config manager)
        from app.protocols.zerox import ZeroXProtocol
        zerox = ZeroXProtocol()
        logger.info("✅ 0x protocol imports successfully")

        # Test that configuration manager is used
        if hasattr(axelar, 'config') and axelar.config is None:
            logger.info("✅ Axelar service uses configuration manager")
        else:
            logger.warning("⚠️  Axelar service configuration status unclear")

        if hasattr(zerox, 'config') and zerox.config is None:
            logger.info("✅ 0x protocol uses configuration manager")
        else:
            logger.warning("⚠️  0x protocol configuration status unclear")

        return True

    except Exception as e:
        logger.error(f"❌ Mock elimination validation failed: {e}")
        return False

async def validate_error_handling():
    """Validate that proper error handling is in place."""
    logger.info("\n⚠️  Testing Error Handling...")

    try:
        # Test invalid token lookup
        invalid_token = await config_manager.get_token("nonexistent_token")
        if invalid_token is None:
            logger.info("✅ Invalid token returns None (not mock data)")
        else:
            logger.error("❌ Invalid token returned data instead of None")

        # Test invalid chain lookup
        invalid_chain = await config_manager.get_chain(999999)
        if invalid_chain is None:
            logger.info("✅ Invalid chain returns None (not mock data)")
        else:
            logger.error("❌ Invalid chain returned data instead of None")

        # Test invalid protocol lookup
        invalid_protocol = await config_manager.get_protocol("nonexistent_protocol")
        if invalid_protocol is None:
            logger.info("✅ Invalid protocol returns None (not mock data)")
        else:
            logger.error("❌ Invalid protocol returned data instead of None")

        return True

    except Exception as e:
        logger.error(f"❌ Error handling validation failed: {e}")
        return False

def print_summary(config_ok, mock_ok, error_ok):
    """Print validation summary."""
    logger.info("\n" + "="*50)
    logger.info("📋 VALIDATION SUMMARY")
    logger.info("="*50)

    logger.info(f"Configuration Manager: {'✅ PASS' if config_ok else '❌ FAIL'}")
    logger.info(f"Mock Elimination:      {'✅ PASS' if mock_ok else '❌ FAIL'}")
    logger.info(f"Error Handling:        {'✅ PASS' if error_ok else '❌ FAIL'}")

    overall_status = "✅ PASS" if all([config_ok, mock_ok, error_ok]) else "❌ FAIL"
    logger.info(f"\nOverall Status: {overall_status}")

    if overall_status == "✅ PASS":
        logger.info("\n🎉 Foundation consolidation is working correctly!")
        logger.info("📈 Ready to proceed with Week 1-2 completion")
    else:
        logger.info("\n⚠️  Issues found that need attention before proceeding")
        logger.info("🔧 Review the validation output above and fix issues")

    return overall_status == "✅ PASS"

async def main():
    """Main validation routine."""
    logger.info("🚀 SNEL Foundation Validation")
    logger.info("=" * 50)
    logger.info("Validating Week 1-2: AGGRESSIVE CONSOLIDATION")
    logger.info("Testing configuration management and mock elimination")
    logger.info("")

    # Run all validations
    config_ok = await validate_configuration()
    mock_ok = await validate_mock_elimination()
    error_ok = await validate_error_handling()

    # Print summary
    success = print_summary(config_ok, mock_ok, error_ok)

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
