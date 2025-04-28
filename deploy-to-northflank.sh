#!/bin/bash

# Script to deploy the Stable Snel backend to Northflank

# Check if Northflank CLI is installed
if ! command -v northflank &> /dev/null; then
    echo "Northflank CLI not found. Installing..."
    npm install -g @northflank/cli
fi

# Check if user is logged in to Northflank
echo "Checking Northflank login status..."
northflank whoami || northflank login

# Ask for project name
read -p "Enter your Northflank project name (default: stable-snel): " PROJECT_NAME
PROJECT_NAME=${PROJECT_NAME:-stable-snel}

# Create project if it doesn't exist
echo "Creating project $PROJECT_NAME if it doesn't exist..."
northflank projects create --name "$PROJECT_NAME" --region us-east-1 || true

# Create Redis add-on
echo "Creating Redis add-on..."
northflank addons create redis --project "$PROJECT_NAME" --name stable-snel-redis --plan hobby || true

# Get Redis URL
echo "Getting Redis URL..."
REDIS_URL=$(northflank addons get --project "$PROJECT_NAME" --name stable-snel-redis --output json | jq -r '.connection_strings.url')

# Create environment variables
echo "Creating environment variables..."
northflank secrets create --project "$PROJECT_NAME" --name stable-snel-env --secret-type environment || true

# Add environment variables
echo "Adding environment variables..."
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key API_V1_STR --value "/api/v1"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key PROJECT_NAME --value "Stable Snel API"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key REDIS_URL --value "$REDIS_URL"

# Ask for API keys
read -p "Enter your Brian API key: " BRIAN_API_KEY
read -p "Enter your 0x API key: " ZEROX_API_KEY
read -p "Enter your Gemini API key: " GEMINI_API_KEY
read -p "Enter your Telegram bot token: " TELEGRAM_BOT_TOKEN
read -p "Enter your Coingecko API key: " COINGECKO_API_KEY
read -p "Enter your Moralis API key: " MORALIS_API_KEY
read -p "Enter your Alchemy key: " ALCHEMY_KEY

# Add API keys to environment variables
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key BRIAN_API_KEY --value "$BRIAN_API_KEY"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key BRIAN_API_URL --value "https://api.brianknows.org/api/v0"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key DISABLE_SSL_VERIFY --value "false"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key ZEROX_API_KEY --value "$ZEROX_API_KEY"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key GEMINI_API_KEY --value "$GEMINI_API_KEY"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key TELEGRAM_BOT_TOKEN --value "$TELEGRAM_BOT_TOKEN"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key COINGECKO_API_KEY --value "$COINGECKO_API_KEY"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key MORALIS_API_KEY --value "$MORALIS_API_KEY"
northflank secrets update --project "$PROJECT_NAME" --name stable-snel-env --key ALCHEMY_KEY --value "$ALCHEMY_KEY"

# Deploy the backend service
echo "Deploying backend service..."
northflank services create --project "$PROJECT_NAME" --name stable-snel-backend \
    --git-repo "$(git config --get remote.origin.url)" \
    --git-branch "$(git rev-parse --abbrev-ref HEAD)" \
    --build-context "./backend" \
    --dockerfile "./backend/Dockerfile" \
    --port 8000 \
    --secret-group stable-snel-env \
    --cpu 0.5 \
    --memory 1Gi \
    --min-instances 1 \
    --max-instances 3 \
    --health-path "/health" \
    --health-port 8000

# Create a public domain
echo "Creating public domain..."
northflank domains create --project "$PROJECT_NAME" --service stable-snel-backend \
    --port 8000 --name stable-snel-api

# Get the domain URL
DOMAIN_URL=$(northflank domains list --project "$PROJECT_NAME" --output json | jq -r '.[0].url')

echo "Deployment complete!"
echo "Your backend is now available at: $DOMAIN_URL"
echo ""
echo "Next steps:"
echo "1. Update your frontend environment variable NEXT_PUBLIC_API_URL to point to $DOMAIN_URL"
echo "2. Redeploy your frontend on Vercel"
echo ""
echo "For more information, see NORTHFLANK_DEPLOYMENT.md"
