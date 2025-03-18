#!/bin/bash

# Fix Redis SSL Connection Script

echo "🔄 Starting deployment to fix Redis SSL connection issue..."

# Ensure we're in the main branch
git checkout main || { echo "❌ Failed to checkout main branch"; exit 1; }

# Pull latest changes
git pull

# Add the fixed file
git add app/services/wallet_service.py

# Commit the changes
git commit -m "Fix Redis SSL connection for Upstash in serverless environment"

# Push to the main branch
git push

echo "✅ Changes pushed to main branch. Vercel should automatically deploy the fix."
echo "🔍 Check the Vercel dashboard for deployment status."
echo "The changes fix the 'AbstractConnection.__init__() got an unexpected keyword argument 'ssl'' error"
echo "by using ssl_cert_reqs parameter instead of the ssl parameter for Upstash Redis connection." 