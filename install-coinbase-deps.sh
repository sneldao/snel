#!/bin/bash
set -e

echo "Installing dependencies for Coinbase CDP SDK integration"

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "pip could not be found. Make sure Python and pip are installed."
    exit 1
fi

# Install required Python packages
echo "Installing required Python packages..."
pip install cdp-sdk eth-account web3 python-dotenv redis

# Create a simple .env.local.example file if it doesn't exist
if [ ! -f .env.local.example ]; then
    echo "Creating example environment file..."
    cat > .env.local.example << EOF
# Coinbase Developer Platform credentials
# Get these from the Coinbase Developer Platform portal: https://www.coinbase.com/cloud/
CDP_API_KEY_NAME=your_api_key_name
CDP_API_KEY_PRIVATE_KEY=your_api_key_private_key

# Redis connection URL
REDIS_URL=redis://localhost:6379/0

# Other environment variables
TELEGRAM_TOKEN=your_telegram_bot_token
EOF
    echo "Created .env.local.example file"
fi

echo "Installing dependencies for testing and development..."
pip install pytest pytest-asyncio httpx

echo ""
echo "Installation complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Create your Coinbase Developer Platform API keys at https://www.coinbase.com/cloud/"
echo "2. Add your API keys to .env.local file (copy from .env.local.example)"
echo "3. Run the test script: ./test-coinbase-wallet.py"
echo ""
echo "For Smart Wallet functionality:"
echo "- Base Sepolia testnet will be used by default"
echo "- You can get testnet ETH from https://faucet.base.org/"
echo ""
echo "Happy coding! 🚀" 