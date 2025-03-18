#!/usr/bin/env python
import os
import sys
import logging
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

# Check if CDP SDK is installed
try:
    # Force Python to look in the current virtualenv
    # This helps when the script is run in a different context
    import importlib.util
    if importlib.util.find_spec("cdp") is None:
        logger.error("CDP SDK is not installed. Install it with: pip install cdp-sdk")
        logger.info("For more information, visit: https://docs.developer.coinbase.com/coinbase-developer-platform/docs/quickstart")
        exit(1)
    
    from cdp import Cdp, Wallet, SmartWallet, Transaction, FunctionCall, EncodedCall
    logger.info("CDP SDK is installed")
except ImportError as e:
    logger.error(f"Error importing CDP SDK: {e}")
    logger.error("CDP SDK is not installed correctly. Install it with: pip install cdp-sdk")
    logger.info("For more information, visit: https://docs.developer.coinbase.com/coinbase-developer-platform/docs/quickstart")
    exit(1)

# Test if we have API keys in environment
CDP_API_KEY_NAME = os.getenv("CDP_API_KEY_NAME", "")
CDP_API_KEY_PRIVATE_KEY = os.getenv("CDP_API_KEY_PRIVATE_KEY", "")

if not CDP_API_KEY_NAME or not CDP_API_KEY_PRIVATE_KEY:
    logger.warning("Coinbase CDP API keys not found in environment variables")
    logger.info("You will need to configure CDP API keys to use this script")
    logger.info("Visit: https://docs.developer.coinbase.com/coinbase-developer-platform/docs/access-cdp")
    logger.info("Set CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY in your .env.local file")

def test_wallet_creation():
    """Test creating a wallet with Coinbase CDP SDK"""
    try:
        logger.info("Testing wallet creation with CDP SDK")
        
        # First check if API keys are available
        if not CDP_API_KEY_NAME or not CDP_API_KEY_PRIVATE_KEY:
            logger.error("Cannot create wallet without CDP API keys")
            return False

        # Configure the CDP SDK
        logger.info("Configuring CDP SDK with API keys")
        Cdp.configure(CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE_KEY)
        logger.info("CDP SDK configured successfully")
        
        # Create a new wallet
        logger.info("Creating a new wallet...")
        wallet = Wallet.create(network_id="base-sepolia")
        
        # Get default address
        address = wallet.default_address
        logger.info(f"Created wallet with default address: {address.address_id}")
        
        # Get wallet balance
        balance = wallet.balance("eth")
        logger.info(f"Wallet balance: {balance} ETH")
        
        # Save wallet information to a local file for future reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wallet_info_file = f"wallet_info_{timestamp}.txt"
        
        with open(wallet_info_file, "w") as f:
            f.write(f"Wallet created at: {datetime.now().isoformat()}\n")
            f.write(f"Network: base-sepolia\n")
            f.write(f"Default address: {address.address_id}\n")
            f.write(f"Initial balance: {balance} ETH\n")
        
        logger.info(f"Wallet information saved to {wallet_info_file}")
        
        # Return success
        return True
        
    except Exception as e:
        logger.exception(f"Error creating wallet with CDP SDK: {e}")
        return False

def test_smart_wallet_creation():
    """Test creating a smart wallet with Coinbase CDP SDK"""
    try:
        logger.info("Testing smart wallet creation with CDP SDK")
        
        # First check if API keys are available
        if not CDP_API_KEY_NAME or not CDP_API_KEY_PRIVATE_KEY:
            logger.error("Cannot create smart wallet without CDP API keys")
            return False

        # Check if we have eth_account module
        try:
            from eth_account import Account
            logger.info("eth_account module is installed")
        except ImportError:
            logger.error("eth_account module is not installed. Install it with: pip install eth-account")
            return False

        # Configure the CDP SDK if not already configured
        logger.info("Configuring CDP SDK with API keys")
        Cdp.configure(CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE_KEY)
        logger.info("CDP SDK configured successfully")
        
        # Create owner account
        logger.info("Creating owner account...")
        private_key = Account.create().key
        owner = Account.from_key(private_key)
        logger.info(f"Created owner account with address: {owner.address}")
        
        # Create smart wallet
        logger.info("Creating smart wallet...")
        smart_wallet = SmartWallet.create(account=owner)
        smart_wallet_address = smart_wallet.address
        logger.info(f"Created smart wallet with address: {smart_wallet_address}")
        
        # Save smart wallet information to a local file for future reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wallet_info_file = f"smart_wallet_info_{timestamp}.txt"
        
        with open(wallet_info_file, "w") as f:
            f.write(f"Smart wallet created at: {datetime.now().isoformat()}\n")
            f.write(f"Network: base-sepolia\n")
            f.write(f"Smart wallet address: {smart_wallet_address}\n")
            f.write(f"Owner address: {owner.address}\n")
            f.write(f"Private key (KEEP SECURE): {private_key.hex()}\n")
        
        logger.info(f"Smart wallet information saved to {wallet_info_file}")
        
        # Return success
        return True
        
    except Exception as e:
        logger.exception(f"Error creating smart wallet with CDP SDK: {e}")
        return False

def test_wallet_faucet():
    """Test using the faucet to fund a wallet with CDP SDK"""
    try:
        logger.info("Testing wallet faucet with CDP SDK")
        
        # First check if API keys are available
        if not CDP_API_KEY_NAME or not CDP_API_KEY_PRIVATE_KEY:
            logger.error("Cannot use faucet without CDP API keys")
            return False

        # Configure the CDP SDK
        logger.info("Configuring CDP SDK with API keys")
        Cdp.configure(CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE_KEY)
        logger.info("CDP SDK configured successfully")
        
        # Create a new wallet on testnet
        logger.info("Creating a new wallet on base-sepolia...")
        wallet = Wallet.create(network_id="base-sepolia")
        address = wallet.default_address
        logger.info(f"Created wallet with default address: {address.address_id}")
        
        # Get initial balance
        initial_balance = wallet.balance("eth")
        logger.info(f"Initial wallet balance: {initial_balance} ETH")
        
        # Use faucet to fund wallet
        logger.info("Using faucet to fund wallet...")
        faucet_tx = wallet.faucet()
        
        # Wait for faucet transaction to complete
        logger.info("Waiting for faucet transaction to complete...")
        faucet_tx.wait()
        
        # Get new balance
        new_balance = wallet.balance("eth")
        logger.info(f"New wallet balance after faucet: {new_balance} ETH")
        
        # Save wallet information to a local file for future reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wallet_info_file = f"funded_wallet_info_{timestamp}.txt"
        
        with open(wallet_info_file, "w") as f:
            f.write(f"Wallet created and funded at: {datetime.now().isoformat()}\n")
            f.write(f"Network: base-sepolia\n")
            f.write(f"Default address: {address.address_id}\n")
            f.write(f"Initial balance: {initial_balance} ETH\n")
            f.write(f"Balance after faucet: {new_balance} ETH\n")
            f.write(f"Faucet transaction: {faucet_tx}\n")
        
        logger.info(f"Funded wallet information saved to {wallet_info_file}")
        
        # Return success
        return True
        
    except Exception as e:
        logger.exception(f"Error using wallet faucet with CDP SDK: {e}")
        return False

def main():
    """Run tests for Coinbase CDP SDK"""
    logger.info("Running tests for Coinbase CDP SDK")
    
    # Test wallet creation
    wallet_creation_result = test_wallet_creation()
    logger.info(f"Wallet creation test: {'SUCCESS' if wallet_creation_result else 'FAILED'}")
    
    # Test smart wallet creation
    smart_wallet_creation_result = test_smart_wallet_creation()
    logger.info(f"Smart wallet creation test: {'SUCCESS' if smart_wallet_creation_result else 'FAILED'}")
    
    # Test wallet faucet
    wallet_faucet_result = test_wallet_faucet()
    logger.info(f"Wallet faucet test: {'SUCCESS' if wallet_faucet_result else 'FAILED'}")
    
    # Summary
    logger.info("\n----- Test Summary -----")
    logger.info(f"Wallet creation: {'SUCCESS' if wallet_creation_result else 'FAILED'}")
    logger.info(f"Smart wallet creation: {'SUCCESS' if smart_wallet_creation_result else 'FAILED'}")
    logger.info(f"Wallet faucet: {'SUCCESS' if wallet_faucet_result else 'FAILED'}")
    
    if wallet_creation_result or smart_wallet_creation_result:
        logger.info("\nINSTRUCTIONS:")
        logger.info("1. To integrate with your Telegram bot, use the WalletService approach")
        logger.info("2. Replace Particle Auth with Coinbase CDP SDK in your WalletService class")
        logger.info("3. For production, consider using Coinbase-Managed Wallets for added security")
        logger.info("4. Remember to secure wallet information properly in Redis or other persistent storage")
    else:
        logger.error("\nAll tests failed. Please check your CDP API keys and try again.")
        logger.info("For more information, visit: https://docs.developer.coinbase.com/coinbase-developer-platform/docs/access-cdp")

if __name__ == "__main__":
    main() 