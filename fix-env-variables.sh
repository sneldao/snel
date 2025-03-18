#!/bin/bash

# Exit on error
set -e

echo "Starting environment variables fix deployment..."

# Pull latest changes
git pull

# Make sure local environment variables are loaded
set -a
source .env.local
set +a

# Deploy the code changes
echo "Deploying environment configuration fix..."

# Commit changes
git add app/core/config.py
git commit -m "Fix Pydantic Settings to accept all environment variables"

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

echo "Deployment script completed."
echo "After deployment is complete, check if the application starts correctly and Telegram webhooks are working" 