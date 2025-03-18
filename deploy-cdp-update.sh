#!/bin/bash
set -e

echo "Starting deployment of Coinbase CDP Wallet update..."

# Check if on main branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "main" ]; then
    echo "Warning: You are not on the main branch. Current branch: $current_branch"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# Load environment variables
if [ -f .env.local ]; then
    echo "Loading environment from .env.local"
    export $(grep -v '^#' .env.local | xargs)
else
    echo "Error: .env.local file not found"
    exit 1
fi

# Check required environment variables
if [ -z "$CDP_API_KEY_NAME" ] || [ -z "$CDP_API_KEY_PRIVATE_KEY" ]; then
    echo "Error: CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY must be set in .env.local"
    echo "Please get your API keys from https://www.coinbase.com/cloud"
    exit 1
fi

# Create isolated environment for CDP if it doesn't exist
if [ ! -d "cdp-venv" ]; then
    echo "Creating isolated CDP environment..."
    ./isolate-cdp-env.sh
else
    echo "Isolated CDP environment already exists."
fi

# Set USE_CDP_SDK to true in .env.local if not already set
if ! grep -q "USE_CDP_SDK=true" .env.local; then
    echo "Setting USE_CDP_SDK=true in .env.local"
    echo "USE_CDP_SDK=true" >> .env.local
fi

# Check if any changes need to be committed
if ! git diff --quiet; then
    echo "There are uncommitted changes in the working directory."
    read -p "Commit these changes before deploying? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "Update environment for Coinbase CDP integration"
    else
        echo "Please commit your changes and run this script again."
        exit 1
    fi
fi

# Create a backup branch
backup_branch="backup-pre-cdp-$(date +%Y%m%d%H%M%S)"
echo "Creating backup branch: $backup_branch"
git checkout -b $backup_branch
git push -u origin $backup_branch
git checkout $current_branch

# Deploy the changes
echo "Deploying to Vercel..."
if [ -n "$VERCEL_DEPLOY_HOOK_URL" ]; then
    curl -X POST $VERCEL_DEPLOY_HOOK_URL
    echo "Deployment triggered via webhook."
else
    if command -v vercel &> /dev/null; then
        vercel --prod
    else
        echo "Vercel CLI not found. Please deploy manually or set VERCEL_DEPLOY_HOOK_URL."
        echo "To deploy manually:"
        echo "1. Push your changes to GitHub"
        echo "2. Run 'vercel --prod' from the command line"
        echo "3. Or deploy from the Vercel dashboard"
    fi
fi

echo ""
echo "Coinbase CDP Wallet update deployment complete!"
echo ""
echo "Changes made:"
echo "1. Replaced Particle Auth with Coinbase CDP Smart Wallet"
echo "2. Updated wallet creation and management logic"
echo "3. Added support for ERC-4337 Account Abstraction wallets"
echo "4. Created isolated Python environment for CDP SDK"
echo "5. Added faucet command for testnet ETH"
echo ""
echo "BotFather Commands Update:"
echo "Use these updated commands in BotFather (/mybots > select your bot > Edit Bot > Edit Commands):"
echo ""
echo "start - Get started with the bot"
echo "help - Show available commands"
echo "connect - Create a new wallet powered by Coinbase"
echo "balance - Check your wallet balance"
echo "price - Check cryptocurrency prices"
echo "swap - Swap tokens"
echo "faucet - Get testnet ETH"
echo "disconnect - Disconnect your wallet"
echo ""
echo "Next steps:"
echo "1. Test the bot by sending /start and /connect commands"
echo "2. Update BotFather commands using the list above"
echo "3. Get testnet ETH from https://faucet.base.org"
echo ""
echo "Happy testing! 🚀" 