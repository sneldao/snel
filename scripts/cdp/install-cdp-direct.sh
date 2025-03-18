#!/bin/bash
set -e

echo "Installing Coinbase CDP SDK directly with pip"

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "pip could not be found. Make sure Python and pip are installed."
    exit 1
fi

# Install CDP SDK with direct dependencies, ignoring conflicts with other packages
echo "Installing CDP SDK and dependencies..."
pip install cdp-sdk==0.21.0 eth-account web3 python-dotenv --no-deps

# Install required dependencies that won't conflict
pip install cryptography==43.0.3

echo "Testing CDP SDK installation..."
python -c "
import os
import sys
import logging
try:
    from cdp import Cdp, Wallet, SmartWallet
    print('CDP SDK imported successfully!')
    
    # Check for API keys
    api_key_name = os.getenv('CDP_API_KEY_NAME', '')
    if api_key_name:
        print(f'Found API key: {api_key_name[:5]}...')
    else:
        print('No API key found in environment variables')
    
    print('Installation test complete!')
except ImportError as e:
    print(f'Error importing CDP SDK: {e}')
    sys.exit(1)
"

echo ""
echo "Installation complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Make sure your .env.local file has your Coinbase CDP API keys"
echo "2. Run the test script: ./test-coinbase-wallet.py"
echo ""
echo "For Smart Wallet functionality:"
echo "- Base Sepolia testnet will be used by default"
echo "- You can get testnet ETH from https://faucet.base.org/"
echo ""
echo "Happy coding! 🚀" 