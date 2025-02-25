#!/bin/bash

# Set NODE_ENV to production
export NODE_ENV=production

# Clear any existing NEXT_PUBLIC_API_URL
unset NEXT_PUBLIC_API_URL

# Install Python packages from requirements.txt
pip install -r requirements.txt

# Install additional packages with specific versions if needed
# Using versions from pyproject.toml
pip install dowse==0.1.6.post1 emp-agents==0.3.0 eth-rpc-py==0.1.26

# Print installed packages for debugging
pip freeze > installed_packages.txt

# Create necessary directories if they don't exist
mkdir -p app/services
mkdir -p app/api/routes
mkdir -p app/utils
mkdir -p app/models
mkdir -p app/agents
mkdir -p api

# Ensure the script exits with success
exit 0 