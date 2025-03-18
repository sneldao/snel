#!/usr/bin/env python3
"""
Test script to verify that the Coinbase CDP SDK is working correctly with SSL verification disabled.
WARNING: This is for testing only. In production, proper SSL verification should be used.
"""

import os
import sys
import logging
import ssl
import urllib3
import inspect
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("cdp-test")

# Monkey patch SSL verification before importing any other modules
try:
    # Disable warnings about insecure requests
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Save the original function
    original_create_urllib3_context = ssl.create_default_context
    original_ssl_context = urllib3.connection.ssl_wrap_socket

    # Create a new wrapper function that disables certificate verification
    def patched_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, 
                                      capath=None, cadata=None):
        context = original_create_urllib3_context(purpose, cafile, capath, cadata)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    # Replace the original function
    ssl.create_default_context = patched_create_default_context
    ssl._create_default_https_context = ssl._create_unverified_context
    
    # Patch urllib3 directly
    def patched_ssl_wrap_socket(sock, keyfile=None, certfile=None, cert_reqs=None, **kwargs):
        kwargs['cert_reqs'] = ssl.CERT_NONE
        return original_ssl_context(sock, keyfile=keyfile, certfile=certfile, cert_reqs=cert_reqs, **kwargs)
    
    # Apply our patch to urllib3
    urllib3.connection.ssl_wrap_socket = patched_ssl_wrap_socket
    
    logger.warning("⚠️ SSL verification disabled for testing purposes only!")
except Exception as e:
    logger.error(f"Failed to patch SSL verification: {e}")

def main():
    """Test Coinbase CDP SDK functionality."""
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
    
    # Now import CDP SDK after SSL patching
    try:
        from cdp import Cdp, SmartWallet
        from eth_account import Account
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        sys.exit(1)
    
    # Configure CDP SDK
    try:
        logger.info("Configuring CDP SDK...")
        # Force insecure mode in the config
        os.environ["OPENSSL_CONF"] = "/dev/null"  # Disables OpenSSL config verification
        os.environ["CDP_VERIFY_SSL"] = "false"    # Signal to CDP SDK to disable SSL verification
        
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