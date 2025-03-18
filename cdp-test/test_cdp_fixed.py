#!/usr/bin/env python3
"""
Test script to verify the Coinbase CDP SDK is working correctly with proper SSL configuration.
This script tests wallet creation and basic operations with SSL certificates properly configured.
"""

import os
import sys
import logging
import ssl
import urllib3
import certifi
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("cdp-test")

def main():
    """Test Coinbase CDP SDK functionality with proper SSL configuration."""
    # Load environment variables from parent directory
    load_dotenv("../.env")
    load_dotenv("../.env.local", override=True)  # Override with .env.local if it exists
    
    logger.info("Testing Coinbase CDP SDK configuration")
    
    # Check required environment variables
    api_key_name = os.getenv("CDP_API_KEY_NAME")
    api_key_private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY")
    
    if not api_key_name or not api_key_private_key:
        logger.error("Missing CDP_API_KEY_NAME or CDP_API_KEY_PRIVATE_KEY environment variables")
        sys.exit(1)
        
    logger.info(f"Using CDP API key: {api_key_name}")
    
    use_managed_wallet = os.getenv("CDP_USE_MANAGED_WALLET", "").lower() in ("true", "1", "yes")
    logger.info(f"Using Coinbase-Managed (2-of-2) wallets: {use_managed_wallet}")
    
    # Configure SSL properly
    try:
        # Set the SSL certificate path to the certifi bundle
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        os.environ['SSL_CERT_FILE'] = certifi.where()
        
        logger.info(f"Using SSL certificate bundle at: {certifi.where()}")
        
        # Make sure the SSL context is using the proper certificates
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        logger.info("SSL properly configured")
    except Exception as e:
        logger.error(f"Error configuring SSL: {e}")
        sys.exit(1)
    
    # Import CDP SDK
    try:
        from cdp import Cdp, SmartWallet
        from eth_account import Account
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        sys.exit(1)
    
    # Configure CDP SDK
    try:
        logger.info("Configuring CDP SDK...")
        Cdp.configure(api_key_name, api_key_private_key)
        logger.info("CDP SDK configured successfully")
        
        # Enable Server-Signer for managed wallets if specified
        if use_managed_wallet:
            Cdp.use_server_signer = True
            logger.info("Server-Signer enabled for Coinbase-Managed wallets")
    except Exception as e:
        logger.error(f"Error configuring CDP SDK: {e}")
        sys.exit(1)
    
    # Create a test wallet
    try:
        # Create an owner account
        logger.info("Creating owner account...")
        private_key = Account.create().key
        owner = Account.from_key(private_key)
        
        # Create a smart wallet
        logger.info("Creating SmartWallet...")
        smart_wallet = SmartWallet.create(account=owner)
        
        logger.info(f"Smart wallet created successfully!")
        logger.info(f"Owner address: {owner.address}")
        logger.info(f"Smart wallet address: {smart_wallet.address}")
        
        # Test faucet on testnet
        try:
            logger.info("Requesting ETH from faucet (this may take a moment)...")
            faucet_tx = smart_wallet.faucet()
            faucet_tx.wait()
            logger.info(f"Faucet transaction completed: {faucet_tx.transaction_hash}")
        except Exception as e:
            logger.warning(f"Faucet request failed (non-critical): {e}")
        
        logger.info("CDP SDK test completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error testing CDP SDK: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 