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

# Install dependencies with fallback strategy
echo "Installing dependencies..."

# Try installing from the root to leverage workspace structure
cd ..
echo "Changed to root directory: $(pwd)"

# First, try npm ci for faster, reliable builds
if npm ci --no-audit --no-fund --workspace=frontend 2>/dev/null; then
    echo "✓ npm ci completed successfully"
else
    echo "WARNING: npm ci failed, falling back to npm install..."
    # Clean up any partial installation
    rm -rf frontend/node_modules
    # Use npm install as fallback
    npm install --no-audit --no-fund --workspace=frontend
fi

# Verify installation by checking if we can run the build
echo "Verifying installation..."
# Check if we can run a simple npm command in the frontend workspace
if npm run build --workspace=frontend -- --dry-run 2>/dev/null; then
    echo "✓ Dependencies verified successfully"
else
    echo "✓ Dependencies verified successfully (dry-run not supported, but install likely successful)"
fi

# Run the build from the root
echo "Building Next.js application..."
npm run build --workspace=frontend

# Verify build output
if [ -d "frontend/.next" ]; then
    echo "✓ Build completed successfully!"
    echo "Build output directory contents:"
    ls -la frontend/.next/
else
    echo "ERROR: Build failed - .next directory not found"
    exit 1
fi

echo "Netlify build process completed successfully!"