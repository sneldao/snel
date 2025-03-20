#!/bin/bash

# Exit on error
set -e

# Install dependencies
echo "Installing dependencies..."
npm install

# Install ESLint and related packages
echo "Installing ESLint..."
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-config-next

# Run the build
echo "Building Next.js app..."
npm run build 