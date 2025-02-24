#!/bin/bash

# Exit on error
set -e

# Print Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p api

# Copy necessary files to root/api directory
cp -r app/* api/
cp kyber.py api/
cp configure_logging.py api/

# Print environment for debugging (excluding sensitive values)
echo "Environment variables set:"
env | grep -v "KEY\|TOKEN\|SECRET\|PASSWORD"

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Ensure the script exits with success
exit 0 