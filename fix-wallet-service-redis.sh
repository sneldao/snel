#!/bin/bash

# Fix WalletService and GeminiService Script

echo "🔄 Starting deployment to fix WalletService Redis and Gemini errors..."

# Ensure we're in the main branch
git checkout main || { echo "❌ Failed to checkout main branch"; exit 1; }

# Pull latest changes
git pull

# Add the fixed files
git add app/services/wallet_service.py app/services/gemini_service.py app/api/dependencies.py

# Commit the changes
git commit -m "Fix Redis and Gemini API handling in serverless environment"

# Push to the main branch
git push

echo "✅ Changes pushed to main branch. Vercel should automatically deploy the fix."
echo "🔍 Check the Vercel dashboard for deployment status."
echo "The changes address the following issues:"
echo "1. Fixed the WalletService to properly handle Redis bytes vs strings"
echo "2. Added dynamic model selection to the GeminiService"
echo "3. Updated dependencies.py to properly initialize both services"
echo "4. Added direct responses for simple greetings to bypass Gemini API" 