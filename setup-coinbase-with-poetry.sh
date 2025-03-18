#!/bin/bash
set -e

echo "Setting up Coinbase CDP SDK integration with Poetry"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    echo "Please restart your terminal or run 'source $HOME/.poetry/env' to use Poetry"
    exit 0
fi

echo "Poetry is installed. Setting up project..."

# Initialize Poetry if pyproject.toml doesn't exist
if [ ! -f pyproject.toml ]; then
    echo "Initializing Poetry project..."
    poetry init --name "dowse-pointless" --description "Pointless crypto assistant with CDP wallet integration" --author "Your Name <your.email@example.com>" --python "^3.10" --no-interaction
fi

# Add required dependencies
echo "Adding required dependencies..."
poetry add cdp-sdk eth-account web3 python-dotenv redis fastapi uvicorn httpx pytest pytest-asyncio

# Create a .env.local.example file if it doesn't exist
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

# Copy test script to make sure it works with Poetry
cat > test-cdp-with-poetry.py << EOF
#!/usr/bin/env python
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

try:
    from cdp import Cdp, Wallet, SmartWallet
    logger.info("CDP SDK is installed and working")
except ImportError as e:
    logger.error(f"Error importing CDP SDK: {e}")
    exit(1)

def main():
    """Test if CDP SDK is working properly with Poetry"""
    logger.info("Testing CDP SDK with Poetry")
    
    # Check for API keys
    api_key_name = os.getenv("CDP_API_KEY_NAME", "")
    api_key_private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY", "")
    
    if not api_key_name or not api_key_private_key:
        logger.warning("CDP API keys not found in environment variables")
        logger.info("Please add your CDP API keys to .env.local file")
    else:
        logger.info("CDP API keys found in environment variables")
    
    logger.info("CDP SDK setup with Poetry is complete!")
    logger.info("To run the full test script, use: poetry run python test-coinbase-wallet.py")

if __name__ == "__main__":
    main()
EOF

# Make the test script executable
chmod +x test-cdp-with-poetry.py

echo ""
echo "Poetry setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Run 'poetry shell' to activate the virtual environment"
echo "2. Run './test-cdp-with-poetry.py' to verify CDP SDK is working"
echo "3. Get your Coinbase Developer Platform API keys at https://www.coinbase.com/cloud/"
echo "4. Add your API keys to .env.local file"
echo "5. Use the full test script with: 'poetry run python test-coinbase-wallet.py'"
echo ""
echo "Benefits of using Poetry:"
echo "- Dependency locking for reproducible builds"
echo "- Easy virtual environment management"
echo "- Simple dependency resolution"
echo "- Project packaging and publishing capabilities"
echo ""
echo "Happy coding! 🚀" 