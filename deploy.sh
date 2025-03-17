#!/bin/bash
# Script to deploy changes to Vercel

# Exit on error
set -e

echo "Starting deployment process..."

# Install dependencies with specific versions
echo "Installing dependencies..."
pip install -r requirements.txt

# Verify OpenAI and HTTPX versions
echo "Verifying OpenAI and HTTPX versions..."
python -c "import openai; print(f'OpenAI version: {openai.__version__}')"
python -c "import httpx; print(f'HTTPX version: {httpx.__version__}')"

# Check for required environment variables
echo "Checking environment variables..."
if [ -z "$OPENAI_API_KEY" ]; then
  echo "Warning: OPENAI_API_KEY is not set. OpenAI features will not work."
fi

if [ -z "$BRIAN_API_KEY" ]; then
  echo "Warning: BRIAN_API_KEY is not set. Brian API features will not work."
fi

if [ -z "$REDIS_URL" ]; then
  echo "Warning: REDIS_URL is not set. Redis features will not work."
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
echo "You can now deploy the application to Vercel." 