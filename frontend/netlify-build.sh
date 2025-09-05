#!/bin/bash

# Exit on error
set -e

echo "Starting Netlify build process..."

# Ensure we're in the frontend directory
cd "$(dirname "$0")"

# Print current directory and Node.js version for debugging
echo "Current directory: $(pwd)"
echo "Node.js version: $(node --version)"
echo "NPM version: $(npm --version)"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found in $(pwd)"
    exit 1
fi

# Clean npm cache to avoid potential issues
echo "Cleaning npm cache..."
npm cache clean --force

# Remove existing node_modules and package-lock.json to ensure clean install
echo "Cleaning existing dependencies..."
rm -rf node_modules package-lock.json

# Install dependencies with legacy peer deps flag to handle potential conflicts
echo "Installing dependencies..."
npm install --legacy-peer-deps

# Verify node_modules exists and has content
if [ ! -d "node_modules" ]; then
    echo "ERROR: node_modules directory not found after npm install"
    exit 1
fi

echo "node_modules directory verified, contains $(ls node_modules | wc -l) packages"

# List some key dependencies to verify installation
echo "Checking key dependencies..."
ls -la node_modules/next/ > /dev/null && echo "✓ Next.js installed" || echo "✗ Next.js missing"
ls -la node_modules/react/ > /dev/null && echo "✓ React installed" || echo "✗ React missing"
ls -la node_modules/@chakra-ui/ > /dev/null && echo "✓ Chakra UI installed" || echo "✗ Chakra UI missing"

# Run the build
echo "Building Next.js application..."
npm run build

echo "Build completed successfully!"