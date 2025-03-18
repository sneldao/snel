#!/bin/bash

# Exit on error
set -e

echo "Starting Telegram webhook fix deployment..."

# Pull latest changes
git pull

# Make sure local environment variables are loaded
set -a
source .env.local
set +a

# Check if TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN is not set. Please set it in .env.local"
    exit 1
fi

# Check if the main domain is set
if [ -z "$MAIN_DOMAIN" ]; then
    echo "Error: MAIN_DOMAIN is not set. Please set it in .env.local"
    echo "Example: MAIN_DOMAIN=https://yourapp.vercel.app"
    exit 1
fi

# Use the webhook path from environment or default to /api/webhook/webhook
WEBHOOK_PATH=${TELEGRAM_WEBHOOK_PATH:-"/api/webhook/webhook"}
FULL_WEBHOOK_URL="${MAIN_DOMAIN}${WEBHOOK_PATH}"

# Verifying the webhook setup with Telegram
echo "Checking current webhook setup..."
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | jq .

# Set the webhook URL to the correct endpoint
echo "Setting webhook to ${FULL_WEBHOOK_URL}..."
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${FULL_WEBHOOK_URL}\"}" | jq .

# Check if there are changes to commit
git diff --quiet app/api/routes/messaging.py || {
    # Deploy the code changes if there are modifications to commit
    echo "Deploying code changes..."

    # Commit changes
    git add app/api/routes/messaging.py
    git commit -m "Fix Telegram webhook handling and update webhook configuration"

    # Push to origin
    git push

    # Trigger Vercel deployment if VERCEL_DEPLOY_HOOK_URL is set
    if [ -n "$VERCEL_DEPLOY_HOOK_URL" ]; then
        echo "Triggering Vercel deployment..."
        curl -X POST "$VERCEL_DEPLOY_HOOK_URL"
    else
        echo "VERCEL_DEPLOY_HOOK_URL not set, skipping automatic deployment"
        echo "Please deploy manually or set VERCEL_DEPLOY_HOOK_URL in .env.local"
    fi
} || {
    echo "No changes to deploy."
}

echo "Deployment script completed."
echo "After deployment is complete, verify webhook again:"
echo "curl -s \"https://api.telegram.org/bot\$TELEGRAM_BOT_TOKEN/getWebhookInfo\" | jq ." 