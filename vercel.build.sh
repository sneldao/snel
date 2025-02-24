#!/bin/bash

# Exit on error
set -e

# Print Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p .vercel/cache

# Copy necessary files
cp -r app .vercel/cache/
cp kyber.py .vercel/cache/
cp configure_logging.py .vercel/cache/
cp api.py .vercel/cache/

# Print environment for debugging (excluding sensitive values)
echo "Environment variables set:"
env | grep -v "KEY\|TOKEN\|SECRET\|PASSWORD"

# Install additional packages with specific versions
pip install dowse==0.1.0 emp-agents==0.2.0.post1 eth-rpc==0.1.26

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Create necessary directories if they don't exist
mkdir -p app/services

# Ensure the script exits with success
exit 0 