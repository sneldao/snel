#!/bin/bash
# Script to deploy Telegram-specific changes to Vercel

# Exit on error
set -e

echo "Starting Telegram-specific deployment..."

# Verify we have the needed files
if [ ! -f "app/agents/telegram_agent.py" ]; then
  echo "Error: Telegram agent file not found!"
  exit 1
fi

# Run basic environment checks for Telegram
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Warning: TELEGRAM_BOT_TOKEN is not set. Telegram bot will not work correctly."
fi

# Add the Telegram agent changes
echo "Adding Telegram agent changes..."
git add app/agents/telegram_agent.py

# Add README changes
echo "Adding README changes..."
git add README.md

# Commit with a descriptive message
echo "Committing changes..."
git commit -m "Fix TelegramAgent Pydantic model and update README with Telegram integration"

# Push to main branch (adjust if you're using a different branch)
echo "Pushing changes to GitHub..."
git push origin main

echo "Changes pushed to GitHub. Vercel should automatically deploy."
echo ""
echo "Don't forget to update BotFather with the command list:"
echo ""
echo "start - Start the bot and get a welcome message"
echo "help - Show a list of available commands"
echo "connect - Connect or create a wallet"
echo "price - Check token price (e.g., /price ETH)"
echo "swap - Create a token swap (e.g., /swap 0.1 ETH for USDC)"
echo "balance - Check your wallet balance"
echo "disconnect - Disconnect your wallet" 