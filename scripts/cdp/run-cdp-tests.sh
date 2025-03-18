#!/bin/bash
set -e

# Activate the virtual environment
source cdp-venv/bin/activate

# Run the test script with the virtual environment's Python
python test-coinbase-wallet.py

# Deactivate the virtual environment
deactivate
