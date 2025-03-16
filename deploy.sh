#!/bin/bash

# Exit on error
set -e

echo "Starting deployment process..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for required environment variables
echo "Checking environment variables..."
if [ -z "$BRIAN_API_KEY" ]; then
  echo "Warning: BRIAN_API_KEY is not set. Brian API features will not work."
fi

if [ -z "$MORALIS_API_KEY" ]; then
  echo "Warning: MORALIS_API_KEY is not set. Token lookups may be limited."
fi

if [ -z "$COINGECKO_API_KEY" ]; then
  echo "Warning: COINGECKO_API_KEY is not set. Token lookups may be limited."
fi

if [ -z "$QUICKNODE_API_KEY" ]; then
  echo "Warning: QUICKNODE_API_KEY is not set. Token lookups may be limited."
fi

# Verify OpenAI module is installed
echo "Verifying OpenAI module..."
python -c "import openai" || { echo "Error: OpenAI module not found. Installing..."; pip install openai==1.14.0; }

# Run tests if available
if [ -d "tests" ]; then
  echo "Running tests..."
  pytest tests/
fi

echo "Deployment preparation complete!"
echo "You can now start the application with: uvicorn app.main:app --reload" 