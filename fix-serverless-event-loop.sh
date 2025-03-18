#!/bin/bash

# Fix Serverless Event Loop Issues Script

echo "🔄 Starting deployment to fix serverless event loop issues..."

# Ensure we're in the main branch
git checkout main || { echo "❌ Failed to checkout main branch"; exit 1; }

# Pull latest changes
git pull

# Add the fixed files
git add app/services/gemini_service.py app/services/wallet_service.py

# Commit the changes
git commit -m "Fix event loop closed errors in serverless environment"

# Push to the main branch
git push

echo "✅ Changes pushed to main branch. Vercel should automatically deploy the fix."
echo "🔍 Check the Vercel dashboard for deployment status."
echo "The changes address two critical issues in serverless environments:"
echo "1. Redis connections being closed by the serverless platform"
echo "2. HTTPX clients failing with 'Event loop is closed' errors"
echo "Both services now properly recreate clients when needed and handle errors gracefully." 