#!/bin/bash

# Exit on error
set -e

echo "Starting Telegram bot deployment process..."

# Install dependencies
echo "Installing dependencies..."
npm install

# Verify ethers.js version
echo "Verifying ethers.js version..."
npm list ethers

# Check for required environment variables
echo "Checking environment variables..."
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN is not set. Bot will not function without it."
  exit 1
fi

if [ -z "$API_URL" ]; then
  echo "Warning: API_URL is not set. Using default http://localhost:8000"
  echo "This will not work in production. Please set API_URL to your backend URL."
fi

# Create build directory if it doesn't exist
echo "Creating build directory..."
mkdir -p build

# Copy necessary files to build directory
echo "Copying files to build directory..."
cp -r src package.json package-lock.json .env* build/

# Verify webhook.js exists
echo "Verifying webhook handler exists..."
if [ ! -f "src/api/webhook.js" ]; then
  echo "Error: src/api/webhook.js not found. Webhook handler is required for Vercel deployment."
  exit 1
fi

echo "Deployment preparation complete!"
echo "You can now deploy the application to Vercel."
echo "Make sure to set the following environment variables in Vercel:"
echo "- TELEGRAM_BOT_TOKEN: Your Telegram bot token"
echo "- API_URL: URL to your backend API"
echo "- NODE_ENV: Set to 'production'" 