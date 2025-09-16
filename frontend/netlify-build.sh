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

# Handle workspace setup by bypassing it for Netlify builds
echo "Checking for package-lock.json..."
if [ ! -f "package-lock.json" ]; then
    echo "No package-lock.json found. Creating minimal lockfile to bypass workspace..."
    
    # Create a minimal package-lock.json with lockfileVersion 2 for compatibility
    cat > package-lock.json << 'EOF'
{
  "name": "snel",
  "version": "0.1.0",
  "lockfileVersion": 2,
  "requires": true,
  "packages": {
    "": {
      "name": "snel",
      "version": "0.1.0",
      "dependencies": {},
      "devDependencies": {},
      "engines": {
        "node": ">=18"
      }
    }
  }
}
EOF
    
    echo "Minimal package-lock.json created. Now running npm install to populate it..."
    npm install --no-audit --no-fund
    echo "Installation completed. Verifying:"
    ls -la package-lock.json
    ls -la node_modules/ | head -5
else
    echo "package-lock.json found. Using npm ci..."
    npm ci --no-audit --no-fund
fi

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