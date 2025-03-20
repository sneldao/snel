#!/bin/bash

# Exit on error
set -e

# Debug: Print current directory and files
echo "Current directory: $(pwd)"
ls -la

# Set NODE_ENV to production
export NODE_ENV=production

# Skip tests during the build
export SKIP_TESTS=1

# Install frontend dependencies first
echo "Installing frontend dependencies..."
cd frontend
npm install
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-config-next
cd ..

# Install Python packages from requirements.txt
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install additional packages with specific versions
echo "Installing additional dependencies..."
python -m pip install pydantic_settings==2.2.1
python -m pip install eth-rpc-py==0.1.26
python -m pip install uvicorn
python -m pip install fastapi

# Print installed packages for debugging
echo "Generating package list..."
python -m pip freeze > installed_packages.txt

# Create necessary directories
echo "Creating directory structure..."
mkdir -p app/services
mkdir -p app/api/routes
mkdir -p app/utils
mkdir -p app/models
mkdir -p app/agents
mkdir -p api

# Create Vercel entry point
echo "Creating Vercel entry point..."
cat > api/index.py << 'EOL'
import sys
import os
from pathlib import Path

# Add the root directory to Python path
root_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, root_dir)

# Import the FastAPI app
from app.main import app

# This is the handler that Vercel will call
handler = app

# Debug: Print environment
print("Environment variables:", dict(os.environ))
print("Python path:", sys.path)
EOL

# Debug: Print final directory structure
echo "Final directory structure:"
ls -R

# Ensure the script exits with success
echo "Build script completed successfully"
exit 0 