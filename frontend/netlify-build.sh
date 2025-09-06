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

# Set Netlify environment variable
export NETLIFY=true

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found in $(pwd)"
    exit 1
fi

# Check current directory contents
echo "Current directory contents:"
ls -la

# Install dependencies
echo "Installing dependencies..."
npm ci --no-audit --no-fund

# Verify installation by checking key dependencies
echo "Verifying installation..."
if [ -d "node_modules" ]; then
    echo "✓ node_modules directory exists"
    echo "✓ Contains $(ls node_modules | wc -l) packages"
else
    echo "ERROR: node_modules directory not found after npm install"
    echo "Directory contents after npm install:"
    ls -la
    exit 1
fi

# Run the build
echo "Building Next.js application..."
npm run build

# Verify build output
if [ -d ".next" ]; then
    echo "✓ Build completed successfully!"
    echo "Build output directory contents:"
    ls -la .next/
else
    echo "ERROR: Build failed - .next directory not found"
    exit 1
fi

echo "Netlify build process completed successfully!"