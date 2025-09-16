#!/bin/bash

# Exit on error
set -e

echo "Starting Netlify build process..."

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

# Handle workspace setup - copy root package-lock.json if it exists
echo "Checking for workspace setup..."
echo "Contents of parent directory:"
ls -la ../
echo "Checking for ../package-lock.json: $([ -f "../package-lock.json" ] && echo "EXISTS" || echo "NOT FOUND")"
echo "Checking for ./package-lock.json: $([ -f "package-lock.json" ] && echo "EXISTS" || echo "NOT FOUND")"

if [ -f "../package-lock.json" ] && [ ! -f "package-lock.json" ]; then
    echo "Copying root package-lock.json to frontend directory..."
    cp ../package-lock.json ./package-lock.json
    echo "Copy completed. Verifying:"
    ls -la package-lock.json
    head -5 package-lock.json
else
    echo "Workspace copy condition not met."
    if [ ! -f "../package-lock.json" ]; then
        echo "  - ../package-lock.json does not exist"
    fi
    if [ -f "package-lock.json" ]; then
        echo "  - ./package-lock.json already exists"
    fi
fi

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