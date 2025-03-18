#!/usr/bin/env python
"""
Standalone script to demonstrate using SmartWalletService directly.

This approach creates a wallet without going through the API or web interface.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

# Detect if running in the CDP isolated environment
try:
    from cdp import Cdp, Wallet, SmartWallet
    CDP_AVAILABLE = True
    logger.info("CDP SDK is available")
except ImportError:
    CDP_AVAILABLE = False
    logger.warning("CDP SDK is not available. Run this script using ./run-with-cdp.sh")
    logger.info("If you haven't set up the isolated environment, run ./isolate-cdp-env.sh first")
    sys.exit(1)

# Path to the SmartWalletService module
sys.path.insert(0, os.getcwd())

try:
    from app.services.smart_wallet_service import SmartWalletService
    logger.info("Successfully imported SmartWalletService")
except ImportError as e:
    logger.error(f"Error importing SmartWalletService: {e}")
    logger.info("This script should be run from the project root directory")
    sys.exit(1)

async def create_wallet(user_id: str) -> Dict[str, Any]:
    """Create a wallet for a user using SmartWalletService."""
    redis_url = os.getenv("REDIS_URL")
    wallet_service = SmartWalletService(redis_url=redis_url)
    
    try:
        # Create a smart wallet
        wallet_data = await wallet_service.create_smart_wallet(user_id, platform="test")
        
        if "error" in wallet_data:
            logger.error(f"Failed to create wallet: {wallet_data['error']}")
            return wallet_data
        
        logger.info(f"Created wallet with address: {wallet_data.get('address')}")
        return wallet_data
    except Exception as e:
        logger.exception(f"Error creating wallet: {e}")
        return {"error": str(e)}

async def get_wallet_balance(user_id: str) -> Dict[str, Any]:
    """Get wallet balance for a user using SmartWalletService."""
    redis_url = os.getenv("REDIS_URL")
    wallet_service = SmartWalletService(redis_url=redis_url)
    
    try:
        # Get wallet balance
        balance_data = await wallet_service.get_wallet_balance(user_id, platform="test")
        
        if "error" in balance_data:
            logger.error(f"Failed to get balance: {balance_data['error']}")
            return balance_data
        
        logger.info(f"Wallet balance: {balance_data}")
        return balance_data
    except Exception as e:
        logger.exception(f"Error getting balance: {e}")
        return {"error": str(e)}

async def main():
    """Run the demo."""
    logger.info("Smart Wallet Service Demo")
    
    # Check if CDP API keys are configured
    api_key_name = os.getenv("CDP_API_KEY_NAME", "")
    api_key_private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY", "")
    
    if not api_key_name or not api_key_private_key:
        logger.error("CDP API keys not found in environment variables")
        logger.info("Please add CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY to your .env.local file")
        return
    
    logger.info("CDP API keys found in environment variables")
    
    # Create a test user ID
    user_id = f"test_user_{int(time.time())}"
    logger.info(f"Creating wallet for test user: {user_id}")
    
    # Create wallet
    wallet_data = await create_wallet(user_id)
    
    if "error" in wallet_data:
        logger.error(f"Demo failed: {wallet_data['error']}")
        return
    
    # Get wallet balance
    balance_data = await get_wallet_balance(user_id)
    
    if "error" in balance_data:
        logger.error(f"Failed to get balance: {balance_data['error']}")
    
    logger.info("\nDemo complete! To use SmartWalletService in your application:")
    logger.info("1. Set USE_CDP_SDK=true in your .env.local file")
    logger.info("2. Update your Telegram bot to use SmartWalletService")
    logger.info("3. Refer to the integration guide: integrating-with-telegram.md")

if __name__ == "__main__":
    import time
    asyncio.run(main()) 