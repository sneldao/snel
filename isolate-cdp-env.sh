#!/bin/bash
set -e

echo "Creating isolated environment for Coinbase CDP SDK"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "python3 could not be found. Make sure Python 3 is installed."
    exit 1
fi

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv cdp-venv

# Activate the virtual environment
echo "Activating virtual environment..."
source cdp-venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install cdp-sdk eth-account web3 python-dotenv redis

# Create a wrapper script to run test-coinbase-wallet.py in the virtual environment
cat > run-cdp-tests.sh << 'EOF'
#!/bin/bash
set -e

# Activate the virtual environment
source cdp-venv/bin/activate

# Run the test script with the virtual environment's Python
python test-coinbase-wallet.py

# Deactivate the virtual environment
deactivate
EOF

# Make the wrapper script executable
chmod +x run-cdp-tests.sh

# Create a wrapper script to use the CDP SDK in the virtual environment
cat > run-with-cdp.sh << 'EOF'
#!/bin/bash
set -e

if [ $# -eq 0 ]; then
    echo "Usage: ./run-with-cdp.sh <python-script.py>"
    exit 1
fi

# Activate the virtual environment
source cdp-venv/bin/activate

# Run the specified script with the virtual environment's Python
python "$@"

# Deactivate the virtual environment
deactivate
EOF

# Make the wrapper script executable
chmod +x run-with-cdp.sh

echo ""
echo "Isolated environment setup complete! 🎉"
echo ""
echo "To run the Coinbase CDP test script:"
echo "  ./run-cdp-tests.sh"
echo ""
echo "To run any Python script with the CDP environment:"
echo "  ./run-with-cdp.sh your-script.py"
echo ""
echo "This approach avoids dependency conflicts with your main project."
echo ""
echo "Next steps:"
echo "1. Make sure your .env.local file has your Coinbase CDP API keys"
echo "2. Run the test script using: ./run-cdp-tests.sh"
echo ""
echo "Happy coding! 🚀"

# Deactivate the virtual environment
deactivate

cat > test-cdp-no-ssl.py << EOF
#!/usr/bin/env python
import os
import sys
import ssl
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

# Disable SSL verification (NOT recommended for production)
ssl._create_default_https_context = ssl._create_unverified_context

try:
    from cdp import Cdp, Wallet, SmartWallet
    logger.info("CDP SDK imported successfully!")
    
    # Check for API keys
    api_key_name = os.getenv('CDP_API_KEY_NAME', '')
    if api_key_name:
        print(f'Found API key: {api_key_name[:5]}...')
        
        # Configure CDP
        api_key_private_key = os.getenv('CDP_API_KEY_PRIVATE_KEY', '')
        Cdp.configure(api_key_name, api_key_private_key)
        
        # Try creating a wallet
        wallet = Wallet.create(network_id="base-sepolia")
        print(f"Created wallet with address: {wallet.address}")
    else:
        print('No API key found in environment variables')
    
    print('Test complete!')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
EOF

chmod +x test-cdp-no-ssl.py 